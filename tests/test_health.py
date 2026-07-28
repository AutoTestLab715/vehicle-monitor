import pytest


@pytest.mark.smoke
class TestHealthSmoke:
    def test_health_returns_ok(self, require_api):
        resp = require_api.health()
        assert resp.status_code == 200
        body = resp.json()
        assert body['status'] == 'ok'
        assert body['backend'] == 'flask'
        assert 'http' in body['protocols']

    def test_list_devices_returns_array(self, require_api):
        resp = require_api.list_devices()
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_nonexistent_device_returns_404(self, require_api):
        resp = require_api.get_device('nonexistent-device-id')
        assert resp.status_code == 404
        assert 'error' in resp.json()
