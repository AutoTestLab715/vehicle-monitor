from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import AlarmRecord, DeviceStatus, RemoteOperationRecord, SensorData, VoiceCommandRecord
from app.mqtt_handler import publish_command
from app.services import is_online, pop_command, process_telemetry, queue_command
from app.validation import ValidationError, parse_limit

api_bp = Blueprint('api', __name__)


@api_bp.errorhandler(ValidationError)
def handle_validation_error(exc):
    payload = {'error': exc.message}
    if exc.field:
        payload['field'] = exc.field
    return jsonify(payload), 400


def _emit_telemetry(socketio, payload):
    device_id = payload['deviceId']
    socketio.emit('telemetry', payload)
    socketio.emit(f'telemetry:{device_id}', payload)


@api_bp.post('/telemetry/<device_id>')
def post_telemetry(device_id):
    body = request.get_json(silent=True) or {}
    payload = process_telemetry(device_id, body, source='http')
    _emit_telemetry(current_app.extensions['socketio'], payload)
    return jsonify({'ok': True, 'serverTime': payload['updatedAt']})


@api_bp.get('/commands/<device_id>')
def get_commands(device_id):
    cmd = pop_command(device_id)
    if cmd:
        return jsonify(cmd)
    return ('', 204)


@api_bp.get('/devices')
def list_devices():
    timeout_ms = current_app.config['ONLINE_TIMEOUT_MS']
    rows = DeviceStatus.query.order_by(DeviceStatus.updated_at.desc()).all()
    result = []
    for row in rows:
        data = row.to_dict()
        data['online'] = is_online(row.updated_at, timeout_ms)
        result.append(data)
    return jsonify(result)


@api_bp.get('/devices/<device_id>')
def get_device(device_id):
    row = DeviceStatus.query.get(device_id)
    if not row:
        return jsonify({'error': 'Device not found'}), 404
    data = row.to_dict()
    data['online'] = is_online(row.updated_at, current_app.config['ONLINE_TIMEOUT_MS'])
    return jsonify(data)


@api_bp.post('/devices/<device_id>/control')
def control_device(device_id):
    body = request.get_json(silent=True) or {}
    action = body.get('action')
    value = body.get('value', True)
    valid_actions = current_app.config['VALID_ACTIONS']

    if not action or action not in valid_actions:
        return jsonify({'error': 'Invalid action', 'validActions': sorted(valid_actions)}), 400

    cmd = queue_command(
        device_id,
        action,
        bool(value),
        source=body.get('source', 'web'),
        operator=body.get('operator', 'anonymous'),
    )
    publish_command(device_id, cmd)
    current_app.extensions['socketio'].emit('commandQueued', {'deviceId': device_id, **cmd})
    return jsonify({'ok': True, 'queued': cmd})


@api_bp.get('/alarms')
def list_alarms():
    device_id = request.args.get('deviceId')
    limit = parse_limit(request.args.get('limit'), 50, 200)
    query = AlarmRecord.query
    if device_id:
        query = query.filter_by(device_id=device_id)
    rows = query.order_by(AlarmRecord.created_at.desc()).limit(limit).all()
    return jsonify([row.to_dict() for row in rows])


@api_bp.get('/operations')
def list_operations():
    device_id = request.args.get('deviceId')
    limit = parse_limit(request.args.get('limit'), 50, 200)
    query = RemoteOperationRecord.query
    if device_id:
        query = query.filter_by(device_id=device_id)
    rows = query.order_by(RemoteOperationRecord.created_at.desc()).limit(limit).all()
    return jsonify([row.to_dict() for row in rows])


@api_bp.get('/voice-commands')
def list_voice_commands():
    device_id = request.args.get('deviceId')
    limit = parse_limit(request.args.get('limit'), 50, 200)
    query = VoiceCommandRecord.query
    if device_id:
        query = query.filter_by(device_id=device_id)
    rows = query.order_by(VoiceCommandRecord.created_at.desc()).limit(limit).all()
    return jsonify([row.to_dict() for row in rows])


@api_bp.get('/history/sensors')
def sensor_history():
    device_id = request.args.get('deviceId')
    if not device_id:
        return jsonify({'error': 'deviceId required'}), 400
    limit = parse_limit(request.args.get('limit'), 60, 500)
    rows = (
        SensorData.query.filter_by(device_id=device_id)
        .order_by(SensorData.recorded_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return jsonify([
        {
            'deviceId': row.device_id,
            'distanceCm': row.distance_cm,
            'temperature': row.temperature,
            'humidity': row.humidity,
            'smokeRaw': row.smoke_raw,
            'fan': row.fan,
            'alarm': row.alarm,
            'windowOpen': row.window_open,
            'alertLevel': row.alert_level,
            'recordedAt': row.recorded_at,
        }
        for row in rows
    ])


@api_bp.get('/history/stats')
def history_stats():
    """各表行数与最早/最新时间，便于确认历史数据是否还在。"""
    device_id = request.args.get('deviceId')
    specs = [
        ('device_status', DeviceStatus, 'device_id', 'updated_at', '每设备仅最新 1 条'),
        ('sensor_data', SensorData, 'id', 'recorded_at', '全部历史上报（只增不删）'),
        ('alarm_records', AlarmRecord, 'id', 'created_at', '报警记录'),
        ('remote_operation_records', RemoteOperationRecord, 'id', 'created_at', '远程操作'),
        ('voice_command_records', VoiceCommandRecord, 'id', 'created_at', '语音指令'),
    ]
    result = []
    for table_name, model, count_col, time_col, desc in specs:
        count_q = db.session.query(func.count(getattr(model, count_col)))
        time_q = db.session.query(
            func.min(getattr(model, time_col)),
            func.max(getattr(model, time_col)),
        )
        if device_id and hasattr(model, 'device_id'):
            count_q = count_q.filter(model.device_id == device_id)
            time_q = time_q.filter(model.device_id == device_id)
        count = count_q.scalar()
        oldest, newest = time_q.one()
        result.append({
            'table': table_name,
            'description': desc,
            'count': count,
            'oldestAt': oldest,
            'newestAt': newest,
        })
    return jsonify(result)


@api_bp.get('/health')
def health():
    return jsonify({
        'status': 'ok',
        'devices': DeviceStatus.query.count(),
        'backend': 'flask',
        'protocols': ['http', 'websocket', 'mqtt'],
    })
