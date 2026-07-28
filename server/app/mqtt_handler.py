import json
import threading

import paho.mqtt.client as mqtt

from app.services import process_telemetry
from app.validation import ValidationError

_mqtt_client = None
_socketio = None
_app = None


def _extract_device_id(topic):
    parts = topic.split('/')
    if len(parts) >= 2:
        return parts[1]
    return 'unknown'


def _on_connect(client, userdata, flags, reason_code, properties=None):
    rc = reason_code
    if hasattr(reason_code, 'value'):
        rc = reason_code.value
    if rc != 0:
        print(f'[MQTT] connect failed: {reason_code}')
        return
    topic = userdata.get('telemetry_topic', 'vehicle/+/telemetry')
    client.subscribe(topic)
    print(f'[MQTT] connected, subscribed: {topic}')


def _on_message(client, userdata, msg):
    if not _app:
        return
    try:
        body = json.loads(msg.payload.decode('utf-8'))
    except json.JSONDecodeError:
        print(f'[MQTT] invalid JSON on {msg.topic}')
        return

    device_id = body.get('deviceId') or _extract_device_id(msg.topic)
    try:
        with _app.app_context():
            payload = process_telemetry(device_id, body, source='mqtt')
            if _socketio:
                _socketio.emit('telemetry', payload)
                _socketio.emit(f'telemetry:{device_id}', payload)
        print(f'[MQTT] telemetry saved: {device_id} topic={msg.topic}')
    except ValidationError as exc:
        print(f'[MQTT] invalid telemetry ({msg.topic}): {exc.message}')
    except Exception as exc:
        print(f'[MQTT] process failed ({msg.topic}): {exc}')


def init_mqtt(app, socketio):
    global _mqtt_client, _socketio, _app
    _app = app
    _socketio = socketio

    broker = app.config['MQTT_BROKER']
    port = app.config['MQTT_PORT']
    username = app.config.get('MQTT_USERNAME') or None
    password = app.config.get('MQTT_PASSWORD') or None

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    if username:
        client.username_pw_set(username, password)

    client.user_data_set({'telemetry_topic': app.config['MQTT_TELEMETRY_TOPIC']})
    client.on_connect = _on_connect
    client.on_message = _on_message

    def _connect():
        try:
            client.connect(broker, port, keepalive=60)
            client.loop_forever()
        except Exception as exc:
            print(f'[MQTT] broker unavailable ({broker}:{port}): {exc}')

    thread = threading.Thread(target=_connect, daemon=True, name='mqtt-client')
    thread.start()
    _mqtt_client = client
    return client


def publish_command(device_id, command):
    if not _mqtt_client or not _mqtt_client.is_connected():
        return False
    topic = f"{_app.config['MQTT_COMMAND_PREFIX']}/{device_id}/commands"
    payload = json.dumps(command, ensure_ascii=False)
    result = _mqtt_client.publish(topic, payload, qos=1)
    return result.rc == mqtt.MQTT_ERR_SUCCESS
