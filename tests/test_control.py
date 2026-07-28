import pytest


@pytest.mark.control
class TestRemoteControl:
    @pytest.mark.parametrize(
        'action,value',
        [
            ('fan', True),
            ('fan', False),
            ('alarm', True),
            ('window', False),
        ],
    )
    def test_valid_control_actions(
        self, require_api, require_db, registered_device, action, value
    ):
        device_id = registered_device
        before_ops = require_db.count_remote_operations(device_id)
        before_pending = require_db.count_pending_commands(device_id)

        resp = require_api.control_device(
            device_id,
            {
                'action': action,
                'value': value,
                'source': 'pytest',
                'operator': 'tester',
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body['ok'] is True
        assert body['queued']['action'] == action
        assert body['queued']['value'] is value

        assert require_db.count_remote_operations(device_id) == before_ops + 1
        assert require_db.count_pending_commands(device_id) == before_pending + 1

        op = require_db.get_latest_operation(device_id)
        assert op['action'] == action
        assert bool(op['value']) is value
        assert op['source'] == 'pytest'
        assert op['operator'] == 'tester'

    def test_invalid_action_returns_400(self, require_api, registered_device):
        resp = require_api.control_device(
            registered_device,
            {'action': 'abc', 'value': True},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert 'validActions' in body
        assert 'fan' in body['validActions']
        assert 'alarm' in body['validActions']

    def test_missing_action_returns_400(self, require_api, registered_device):
        resp = require_api.control_device(registered_device, {'value': True})
        assert resp.status_code == 400
        assert 'validActions' in resp.json()

    def test_poll_command_clears_pending_queue(
        self, require_api, require_db, registered_device
    ):
        device_id = registered_device
        require_api.control_device(
            device_id,
            {'action': 'fan', 'value': True, 'source': 'pytest', 'operator': 'tester'},
        )
        assert require_db.count_pending_commands(device_id) == 1

        poll = require_api.poll_commands(device_id)
        assert poll.status_code == 200
        cmd = poll.json()
        assert cmd['action'] == 'fan'
        assert cmd['value'] is True
        assert isinstance(cmd['queuedAt'], int)

        assert require_db.count_pending_commands(device_id) == 0

        empty_poll = require_api.poll_commands(device_id)
        assert empty_poll.status_code == 204

    def test_operations_api_lists_control_records(
        self, require_api, registered_device
    ):
        device_id = registered_device
        require_api.control_device(
            device_id,
            {'action': 'alarm', 'value': True, 'source': 'web', 'operator': 'tester'},
        )

        resp = require_api.list_operations(device_id)
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) >= 1
        assert rows[0]['deviceId'] == device_id
        assert rows[0]['action'] == 'alarm'
