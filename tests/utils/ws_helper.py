import threading
import time

import socketio


class WsHelper:
    def __init__(self, socket_url: str, timeout: float = 8.0):
        self.socket_url = socket_url.rstrip('/')
        self.timeout = timeout
        self.client = socketio.Client(reconnection=False)
        self._events: dict[str, list] = {}
        self._listening: set[str] = set()
        self._lock = threading.Lock()

    def _append(self, event: str, data):
        with self._lock:
            self._events.setdefault(event, []).append(data)

    def ensure_event_listener(self, event: str):
        if event in self._listening:
            return
        self._listening.add(event)

        @self.client.on(event)
        def _handler(data):
            self._append(event, data)

    def connect(self):
        for event in ('telemetry', 'commandQueued'):
            self.ensure_event_listener(event)
        self.client.connect(
            self.socket_url,
            transports=['websocket', 'polling'],
            wait_timeout=self.timeout,
        )

    def disconnect(self):
        if self.client.connected:
            self.client.disconnect()

    def clear_events(self, event: str | None = None):
        with self._lock:
            if event:
                self._events.pop(event, None)
            else:
                self._events.clear()

    def get_events(self, event: str) -> list:
        with self._lock:
            return list(self._events.get(event, []))

    def wait_for_event(self, event: str, predicate=None, timeout: float | None = None):
        self.ensure_event_listener(event)
        deadline = time.time() + (timeout or self.timeout)
        while time.time() < deadline:
            for item in self.get_events(event):
                if predicate is None or predicate(item):
                    return item
            time.sleep(0.1)
        return None

    def emit(self, event: str, data=None):
        self.client.emit(event, data)
