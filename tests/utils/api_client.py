import requests


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.last_response = None

    def _request(self, method: str, path: str, **kwargs):
        url = f'{self.base_url}{path}' if path.startswith('/') else path
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        self.last_response = resp
        return resp

    def get(self, path: str, **kwargs):
        return self._request('GET', path, **kwargs)

    def post(self, path: str, json=None, **kwargs):
        return self._request('POST', path, json=json, **kwargs)

    def post_raw(self, path: str, data: bytes, content_type: str = 'application/json', **kwargs):
        headers = {'Content-Type': content_type}
        return self._request('POST', path, data=data, headers=headers, **kwargs)

    def health(self):
        return self.get('/health')

    def list_devices(self):
        return self.get('/devices')

    def get_device(self, device_id: str):
        return self.get(f'/devices/{device_id}')

    def post_telemetry(self, device_id: str, payload: dict):
        return self.post(f'/telemetry/{device_id}', json=payload)

    def control_device(self, device_id: str, payload: dict):
        return self.post(f'/devices/{device_id}/control', json=payload)

    def poll_commands(self, device_id: str):
        return self.get(f'/commands/{device_id}')

    def list_alarms(self, device_id: str | None = None, limit: int = 50):
        params = {'limit': limit}
        if device_id:
            params['deviceId'] = device_id
        return self.get('/alarms', params=params)

    def list_operations(self, device_id: str | None = None, limit: int = 50):
        params = {'limit': limit}
        if device_id:
            params['deviceId'] = device_id
        return self.get('/operations', params=params)

    def sensor_history(self, device_id: str, limit: int = 60):
        return self.get('/history/sensors', params={'deviceId': device_id, 'limit': limit})

    def history_stats(self, device_id: str | None = None):
        params = {}
        if device_id:
            params['deviceId'] = device_id
        return self.get('/history/stats', params=params)

    def is_available(self) -> bool:
        try:
            resp = self.health()
            return resp.status_code == 200 and resp.json().get('status') == 'ok'
        except requests.RequestException:
            return False
