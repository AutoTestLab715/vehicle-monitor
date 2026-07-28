import json
import threading
import time

import paho.mqtt.client as mqtt


class MqttHelper:
    def __init__(self, broker: str, port: int, command_prefix: str = 'vehicle'):
        self.broker = broker
        self.port = port
        self.command_prefix = command_prefix

    def _make_client(self):
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            return mqtt.Client()

    def is_available(self, timeout: float = 3.0) -> bool:
        connected = threading.Event()

        def on_connect(client, userdata, flags, reason_code, properties=None):
            rc = reason_code.value if hasattr(reason_code, 'value') else reason_code
            if rc == 0:
                connected.set()

        client = self._make_client()
        client.on_connect = on_connect
        try:
            client.connect(self.broker, self.port, keepalive=30)
            client.loop_start()
            ok = connected.wait(timeout)
            client.loop_stop()
            client.disconnect()
            return ok
        except Exception:
            return False

    def publish_telemetry(self, device_id: str, payload: dict):
        topic = f'{self.command_prefix}/{device_id}/telemetry'
        client = self._make_client()
        client.connect(self.broker, self.port, keepalive=30)
        client.loop_start()
        client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)
        time.sleep(0.2)
        client.loop_stop()
        client.disconnect()

    def wait_for_command(self, device_id: str, timeout: float = 5.0):
        topic = f'{self.command_prefix}/{device_id}/commands'
        result = {}
        received = threading.Event()

        def on_connect(client, userdata, flags, reason_code, properties=None):
            rc = reason_code.value if hasattr(reason_code, 'value') else reason_code
            if rc == 0:
                client.subscribe(topic)

        def on_message(client, userdata, msg):
            result['payload'] = json.loads(msg.payload.decode('utf-8'))
            received.set()

        client = self._make_client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(self.broker, self.port, keepalive=30)
        client.loop_start()

        if not received.wait(timeout):
            client.loop_stop()
            client.disconnect()
            return None

        client.loop_stop()
        client.disconnect()
        return result['payload']
