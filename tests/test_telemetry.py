import pytest


@pytest.mark.telemetry
class TestTelemetryReport:
    def test_post_normal_telemetry(self, require_api, require_db, clean_device, normal_telemetry):
        device_id = clean_device
        before_count = require_db.count_sensor_data(device_id)

        resp = require_api.post_telemetry(device_id, normal_telemetry)
        assert resp.status_code == 200
        body = resp.json()
        assert body['ok'] is True
        assert isinstance(body['serverTime'], int)

        device_resp = require_api.get_device(device_id)
        assert device_resp.status_code == 200
        device = device_resp.json()
        assert device['deviceId'] == device_id
        assert device['distanceCm'] == pytest.approx(normal_telemetry['distanceCm'])
        assert device['temperature'] == pytest.approx(normal_telemetry['temperature'])
        assert device['humidity'] == pytest.approx(normal_telemetry['humidity'])
        assert device['smokeRaw'] == normal_telemetry['smokeRaw']
        assert device['alertLevel'] == 'ok'
        assert device['online'] is True

        assert require_db.count_sensor_data(device_id) == before_count + 1
        assert require_db.count_device_status(device_id) == 1

        status_row = require_db.get_device_status(device_id)
        assert float(status_row['distance_cm']) == pytest.approx(normal_telemetry['distanceCm'])
        assert status_row['alert_level'] == 'ok'

        sensor_row = require_db.get_latest_sensor_row(device_id)
        assert sensor_row['source'] == 'http'
        assert float(sensor_row['distance_cm']) == pytest.approx(normal_telemetry['distanceCm'])

    def test_sensor_data_increments_on_each_report(
        self, require_api, require_db, clean_device, normal_telemetry
    ):
        device_id = clean_device

        require_api.post_telemetry(device_id, normal_telemetry)
        require_api.post_telemetry(device_id, normal_telemetry)

        assert require_db.count_sensor_data(device_id) == 2
        assert require_db.count_device_status(device_id) == 1

    def test_post_danger_telemetry_alert_and_db(
        self, require_api, require_db, clean_device, danger_telemetry
    ):
        device_id = clean_device
        before_alarms = require_db.count_alarm_records(device_id)

        resp = require_api.post_telemetry(device_id, danger_telemetry)
        assert resp.status_code == 200

        device = require_api.get_device(device_id).json()
        assert device['alertLevel'] == 'danger'
        assert device['fan'] is True
        assert device['alarm'] is True
        assert device['windowOpen'] is True

        status_row = require_db.get_device_status(device_id)
        assert status_row['alert_level'] == 'danger'
        assert bool(status_row['fan']) is True
        assert bool(status_row['alarm']) is True
        assert bool(status_row['window_open']) is True

        alarm_count = require_db.count_alarm_records(device_id)
        assert alarm_count > before_alarms
        assert alarm_count >= 4

        alarms = require_db.fetch_all(
            'SELECT alarm_type, level FROM alarm_records WHERE device_id = %s',
            (device_id,),
        )
        alarm_types = {row['alarm_type'] for row in alarms}
        assert 'distance' in alarm_types
        assert 'smoke' in alarm_types
        assert 'temperature' in alarm_types

    def test_api_and_db_values_match(
        self, require_api, require_db, clean_device, normal_telemetry
    ):
        device_id = clean_device
        normal_telemetry['distanceCm'] = 88.8
        normal_telemetry['temperature'] = 29.3

        require_api.post_telemetry(device_id, normal_telemetry)

        device = require_api.get_device(device_id).json()
        status_row = require_db.get_device_status(device_id)
        sensor_row = require_db.get_latest_sensor_row(device_id)

        assert device['distanceCm'] == pytest.approx(float(status_row['distance_cm']))
        assert device['temperature'] == pytest.approx(float(status_row['temperature']))
        assert float(sensor_row['distance_cm']) == pytest.approx(device['distanceCm'])
        assert float(sensor_row['temperature']) == pytest.approx(device['temperature'])
