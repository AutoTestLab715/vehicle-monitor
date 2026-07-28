import pytest


@pytest.mark.history
class TestHistoryApi:
    def test_sensor_history_returns_records_in_order(
        self, require_api, require_db, clean_device, normal_telemetry
    ):
        device_id = clean_device
        t1 = dict(normal_telemetry, distanceCm=40.0)
        t2 = dict(normal_telemetry, distanceCm=50.0)

        require_api.post_telemetry(device_id, t1)
        require_api.post_telemetry(device_id, t2)

        resp = require_api.sensor_history(device_id)
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 2
        assert rows[0]['distanceCm'] == pytest.approx(40.0)
        assert rows[1]['distanceCm'] == pytest.approx(50.0)
        assert rows[0]['deviceId'] == device_id

    def test_sensor_history_requires_device_id(self, require_api):
        resp = require_api.get('/history/sensors')
        assert resp.status_code == 400
        assert 'deviceId' in resp.json()['error']

    def test_history_stats_includes_core_tables(
        self, require_api, require_db, clean_device, normal_telemetry
    ):
        device_id = clean_device
        require_api.post_telemetry(device_id, normal_telemetry)

        resp = require_api.history_stats(device_id)
        assert resp.status_code == 200
        rows = resp.json()
        tables = {row['table'] for row in rows}
        assert 'device_status' in tables
        assert 'sensor_data' in tables
        assert 'alarm_records' in tables
        assert 'remote_operation_records' in tables

        sensor_stats = next(row for row in rows if row['table'] == 'sensor_data')
        assert sensor_stats['count'] >= 1
        assert sensor_stats['newestAt'] is not None

        status_stats = next(row for row in rows if row['table'] == 'device_status')
        assert status_stats['count'] == 1
