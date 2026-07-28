import pytest

from conftest import make_telemetry


@pytest.mark.alarm
class TestAlarmLinkage:
    def test_distance_danger_creates_collision_alarm(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        payload = make_telemetry(
            distanceCm=12,
            alarm=True,
            alerts={'distanceDanger': True},
        )

        resp = require_api.post_telemetry(device_id, payload)
        assert resp.status_code == 200

        device = require_api.get_device(device_id).json()
        assert device['alertLevel'] == 'danger'
        assert device['alarm'] is True

        alarm = require_db.get_latest_alarm(device_id, 'distance')
        assert alarm is not None
        assert alarm['level'] == 'danger'
        assert '碰撞危险' in alarm['message']
        assert float(alarm['distance_cm']) == pytest.approx(12)

    def test_temp_warn_creates_temperature_alarm(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        payload = make_telemetry(
            temperature=37,
            fan=True,
            alerts={'tempWarn': True},
        )

        require_api.post_telemetry(device_id, payload)

        device = require_api.get_device(device_id).json()
        assert device['alertLevel'] == 'warn'
        assert device['fan'] is True

        alarm = require_db.get_latest_alarm(device_id, 'temperature')
        assert alarm is not None
        assert alarm['level'] == 'warn'
        assert '温度预警' in alarm['message']
        assert float(alarm['temperature']) == pytest.approx(37)

    def test_smoke_danger_creates_smoke_alarm(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        payload = make_telemetry(
            smokeRaw=2900,
            alarm=True,
            windowOpen=True,
            alerts={'smokeDanger': True},
        )

        require_api.post_telemetry(device_id, payload)

        device = require_api.get_device(device_id).json()
        assert device['alertLevel'] == 'danger'
        assert device['alarm'] is True
        assert device['windowOpen'] is True

        alarm = require_db.get_latest_alarm(device_id, 'smoke')
        assert alarm is not None
        assert alarm['level'] == 'danger'
        assert '烟雾危险' in alarm['message']
        assert alarm['smoke_raw'] == 2900

    def test_alarm_not_duplicated_when_state_unchanged(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        payload = make_telemetry(
            distanceCm=12,
            alarm=True,
            alerts={'distanceDanger': True},
        )

        require_api.post_telemetry(device_id, payload)
        count_after_first = require_db.count_alarm_records(device_id)

        require_api.post_telemetry(device_id, payload)
        count_after_second = require_db.count_alarm_records(device_id)

        assert count_after_second == count_after_first

    def test_alarm_created_again_after_recovery_and_retrigger(
        self, require_api, require_db, clean_device
    ):
        device_id = clean_device
        danger = make_telemetry(
            distanceCm=12,
            alarm=True,
            alerts={'distanceDanger': True},
        )
        recovered = make_telemetry(
            distanceCm=80,
            alarm=False,
            alerts={'distanceDanger': False},
        )

        require_api.post_telemetry(device_id, danger)
        count_after_danger = require_db.count_alarm_records(device_id)

        require_api.post_telemetry(device_id, recovered)
        require_api.post_telemetry(device_id, danger)
        count_after_retrigger = require_db.count_alarm_records(device_id)

        assert count_after_retrigger == count_after_danger + 1

    def test_alarms_api_returns_records(self, require_api, require_db, clean_device):
        device_id = clean_device
        payload = make_telemetry(
            smokeRaw=2900,
            alerts={'smokeDanger': True},
        )
        require_api.post_telemetry(device_id, payload)

        resp = require_api.list_alarms(device_id)
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) >= 1
        assert rows[0]['deviceId'] == device_id
        assert rows[0]['alarmType'] == 'smoke'
        assert rows[0]['level'] == 'danger'
