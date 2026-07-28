import pytest

from config import BASE_URL
from conftest import make_telemetry
from utils.ws_helper import WsHelper

SOCKET_URL = BASE_URL.replace('/api', '')


@pytest.fixture
def ws_client(require_api):
    helper = WsHelper(SOCKET_URL)
    helper.connect()
    yield helper
    helper.disconnect()


@pytest.mark.websocket
class TestWebSocketRealtime:
    def test_ws_connects_successfully(self, ws_client):
        assert ws_client.client.connected is True

    def test_ws_receives_telemetry_after_http_post(
        self, require_api, ws_client, clean_device, normal_telemetry
    ):
        device_id = clean_device
        ws_client.clear_events('telemetry')

        require_api.post_telemetry(device_id, normal_telemetry)

        payload = ws_client.wait_for_event(
            'telemetry',
            predicate=lambda d: d.get('deviceId') == device_id,
        )
        assert payload is not None
        assert payload['distanceCm'] == pytest.approx(normal_telemetry['distanceCm'])
        assert payload['temperature'] == pytest.approx(normal_telemetry['temperature'])
        assert 'alertLevel' in payload

    def test_ws_receives_device_specific_telemetry_event(
        self, require_api, ws_client, clean_device, normal_telemetry
    ):
        device_id = clean_device
        ws_client.clear_events(f'telemetry:{device_id}')

        custom = dict(normal_telemetry, distanceCm=77.7)
        require_api.post_telemetry(device_id, custom)

        payload = ws_client.wait_for_event(
            f'telemetry:{device_id}',
            predicate=lambda d: d.get('deviceId') == device_id,
        )
        assert payload is not None
        assert payload['distanceCm'] == pytest.approx(77.7)

    def test_ws_control_emits_command_queued(
        self, require_api, require_db, ws_client, registered_device
    ):
        device_id = registered_device
        ws_client.clear_events('commandQueued')

        ws_client.emit(
            'control',
            {'deviceId': device_id, 'action': 'fan', 'value': True},
        )

        payload = ws_client.wait_for_event(
            'commandQueued',
            predicate=lambda d: d.get('deviceId') == device_id and d.get('action') == 'fan',
        )
        assert payload is not None
        assert payload['value'] is True
        assert require_db.count_remote_operations(device_id) >= 1

    def test_ws_subscribe_receives_existing_device_state(
        self, require_api, ws_client, clean_device, normal_telemetry
    ):
        device_id = clean_device
        normal_telemetry['distanceCm'] = 66.6
        require_api.post_telemetry(device_id, normal_telemetry)

        ws_client.disconnect()
        ws_client.clear_events('telemetry')
        ws_client.connect()
        ws_client.emit('subscribe', device_id)

        payload = ws_client.wait_for_event(
            'telemetry',
            predicate=lambda d: d.get('deviceId') == device_id,
        )
        assert payload is not None
        assert payload['distanceCm'] == pytest.approx(66.6)

    def test_ws_invalid_control_is_ignored(
        self, require_api, require_db, ws_client, registered_device
    ):
        device_id = registered_device
        before_ops = require_db.count_remote_operations(device_id)
        ws_client.clear_events('commandQueued')

        ws_client.emit(
            'control',
            {'deviceId': device_id, 'action': 'invalid-action', 'value': True},
        )

        payload = ws_client.wait_for_event('commandQueued', timeout=2)
        assert payload is None
        assert require_db.count_remote_operations(device_id) == before_ops
