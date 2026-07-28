import pytest

from conftest import make_telemetry


@pytest.mark.exception
class TestTelemetryExceptions:
    def test_empty_body_uses_defaults(self, require_api, require_db, clean_device):
        device_id = clean_device
        resp = require_api.post_telemetry(device_id, {})
        assert resp.status_code == 200
        assert resp.json()['ok'] is True

        device = require_api.get_device(device_id).json()
        assert device['distanceCm'] == 0
        assert device['temperature'] == 0
        assert device['humidity'] == 0
        assert device['smokeRaw'] == 0
        assert device['alertLevel'] == 'ok'

    def test_missing_sensor_fields_filled_with_defaults(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        resp = require_api.post_telemetry(device_id, {'alerts': {}})
        assert resp.status_code == 200

        row = require_db.get_latest_sensor_row(device_id)
        assert float(row['distance_cm']) == 0
        assert float(row['temperature']) == 0
        assert row['alert_level'] == 'ok'

    def test_malformed_json_treated_as_empty_body(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        resp = require_api.post_raw(
            f'/telemetry/{device_id}',
            data=b'not-valid-json',
        )
        assert resp.status_code == 200

        device = require_api.get_device(device_id).json()
        assert device['distanceCm'] == 0
        assert device['alertLevel'] == 'ok'

    def test_invalid_temperature_type_returns_400(self, require_api, clean_device):
        device_id = clean_device
        resp = require_api.post_telemetry(device_id, {'temperature': 'abc'})
        assert resp.status_code == 400
        body = resp.json()
        assert body['field'] == 'temperature'
        assert 'number' in body['error']
        assert require_api.get_device(device_id).status_code == 404

    def test_extreme_values_are_stored(self, require_api, require_db, clean_device):
        device_id = clean_device
        payload = make_telemetry(
            distanceCm=-5,
            humidity=999,
            smokeRaw=999999,
        )
        resp = require_api.post_telemetry(device_id, payload)
        assert resp.status_code == 200

        row = require_db.get_latest_sensor_row(device_id)
        assert float(row['distance_cm']) == pytest.approx(-5)
        assert float(row['humidity']) == pytest.approx(999)
        assert row['smoke_raw'] == 999999


@pytest.mark.exception
class TestControlExceptions:
    def test_null_action_returns_400(self, require_api, registered_device):
        resp = require_api.control_device(registered_device, {'action': None, 'value': True})
        assert resp.status_code == 400
        assert 'validActions' in resp.json()

    def test_empty_action_returns_400(self, require_api, registered_device):
        resp = require_api.control_device(registered_device, {'action': '', 'value': True})
        assert resp.status_code == 400

    def test_control_with_no_body_returns_400(self, require_api, registered_device):
        resp = require_api.post(f'/devices/{registered_device}/control', json=None)
        assert resp.status_code == 400


@pytest.mark.exception
class TestQueryExceptions:
    def test_history_invalid_limit_returns_400(self, require_api, clean_device):
        resp = require_api.get(
            '/history/sensors',
            params={'deviceId': clean_device, 'limit': 'bad'},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body['field'] == 'limit'

    def test_history_limit_capped_at_500(self, require_api, clean_device, normal_telemetry):
        device_id = clean_device
        require_api.post_telemetry(device_id, normal_telemetry)

        resp = require_api.get(
            '/history/sensors',
            params={'deviceId': device_id, 'limit': 9999},
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 500

    def test_alarms_limit_capped_at_200(self, require_api):
        resp = require_api.get('/alarms', params={'limit': 9999})
        assert resp.status_code == 200
        assert len(resp.json()) <= 200


@pytest.mark.exception
class TestInfrastructureExceptions:
    def test_bad_db_credentials_not_available(self, bad_db_helper):
        assert bad_db_helper.is_available() is False


@pytest.mark.exception
@pytest.mark.fault
class TestDatabaseFault:
    def test_health_fails_when_mysql_down(self, require_api, mysql_stopped):
        resp = require_api.health()
        assert resp.status_code == 500

    def test_telemetry_fails_when_mysql_down(self, require_api, mysql_stopped, test_device_id):
        resp = require_api.post_telemetry(
            test_device_id,
            make_telemetry(distanceCm=10),
        )
        assert resp.status_code == 500

    def test_control_fails_when_mysql_down(self, require_api, mysql_stopped, test_device_id):
        resp = require_api.control_device(
            test_device_id,
            {'action': 'fan', 'value': True},
        )
        assert resp.status_code == 500
