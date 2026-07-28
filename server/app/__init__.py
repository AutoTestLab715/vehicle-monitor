import time

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from sqlalchemy.exc import OperationalError

from app.db_migrate import ensure_schema
from app.extensions import db
from app.models import DeviceStatus
from app.mqtt_handler import init_mqtt
from app.routes import api_bp
from app.services import queue_command
from config import Config, WEB_DIR


def _init_db(app, retries=10, delay=3):
    with app.app_context():
        for attempt in range(retries):
            try:
                db.create_all()
                ensure_schema()
                print('[DB] tables ready')
                return
            except OperationalError as exc:
                if attempt < retries - 1:
                    print(f'[DB] waiting for MySQL ({attempt + 1}/{retries})...')
                    time.sleep(delay)
                    continue
                raise SystemExit(
                    'MySQL unavailable. Start infrastructure first:\n'
                    '  docker compose up -d\n'
                    '  or demo\\start-infra.bat'
                ) from exc


def create_app():
    app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path='')
    app.config.from_object(Config)
    CORS(app)

    db.init_app(app)
    socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')
    app.extensions['socketio'] = socketio

    app.register_blueprint(api_bp, url_prefix='/api')

    @app.get('/')
    def index():
        return send_from_directory(WEB_DIR, 'index.html')

    @app.get('/<path:path>')
    def static_files(path):
        if path.startswith('api/'):
            return {'error': 'Not found'}, 404
        return send_from_directory(WEB_DIR, path)

    @socketio.on('connect')
    def on_connect():
        print('[WS] client connected')

    @socketio.on('subscribe')
    def on_subscribe(device_id):
        for row in DeviceStatus.query.all():
            socketio.emit('telemetry', row.to_dict())

    @socketio.on('control')
    def on_control(data):
        device_id = data.get('deviceId')
        action = data.get('action')
        value = data.get('value', True)
        if not device_id or action not in app.config['VALID_ACTIONS']:
            return
        cmd = queue_command(device_id, action, bool(value), source='websocket')
        from app.mqtt_handler import publish_command
        publish_command(device_id, cmd)
        socketio.emit('commandQueued', {'deviceId': device_id, **cmd})

    _init_db(app)

    init_mqtt(app, socketio)
    return app, socketio
