import threading
import time

import pytest

from conftest import make_telemetry


@pytest.mark.mqtt
class TestMqttCommunication:
    def test_mqtt_telemetry_persisted_to_db(
        self, require_api, require_db, require_mqtt, clean_device
    ):
        device_id = clean_device
        payload = make_telemetry(distanceCm=33.3, temperature=28.8)
        payload['deviceId'] = device_id

        require_mqtt.publish_telemetry(device_id, payload)

        deadline = time.time() + 5
        while time.time() < deadline:
            if require_db.count_sensor_data(device_id) >= 1:
                break
            time.sleep(0.3)
        else:
            pytest.fail('MQTT 上报后 sensor_data 未入库，请确认 Flask 已连接 MQTT Broker')

        row = require_db.get_latest_sensor_row(device_id)
        assert row['source'] == 'mqtt'
        assert float(row['distance_cm']) == pytest.approx(33.3)
        assert float(row['temperature']) == pytest.approx(28.8)

        device = require_api.get_device(device_id).json()
        assert device['distanceCm'] == pytest.approx(33.3)

    def test_control_command_published_to_mqtt_topic(
        self, require_api, require_mqtt, registered_device
    ):
        device_id = registered_device
        result = {}

        def listen():
            result['payload'] = require_mqtt.wait_for_command(device_id, timeout=6)

        listener = threading.Thread(target=listen, daemon=True)
        listener.start()
        time.sleep(0.5)

        resp = require_api.control_device(
            device_id,
            {'action': 'fan', 'value': True, 'source': 'pytest', 'operator': 'tester'},
        )
        assert resp.status_code == 200

        listener.join(timeout=7)
        payload = result.get('payload')
        assert payload is not None, '未在 MQTT commands 主题收到控制指令'
        assert payload['action'] == 'fan'
        assert payload['value'] is True
