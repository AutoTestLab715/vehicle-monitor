import subprocess
import time


MYSQL_SERVICE_CANDIDATES = ('MySQL84', 'MySQL80')


def detect_mysql_service() -> str | None:
    for name in MYSQL_SERVICE_CANDIDATES:
        result = subprocess.run(
            ['sc', 'query', name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return name
    return None


def is_service_running(service_name: str) -> bool:
    result = subprocess.run(
        ['sc', 'query', service_name],
        capture_output=True,
        text=True,
        check=False,
    )
    return 'RUNNING' in result.stdout


def stop_mysql_service(service_name: str) -> tuple[bool, str]:
    if not is_service_running(service_name):
        return True, 'already stopped'
    result = subprocess.run(
        ['net', 'stop', service_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or '').strip()
        return False, message
    deadline = time.time() + 15
    while time.time() < deadline:
        if not is_service_running(service_name):
            return True, 'stopped'
        time.sleep(0.5)
    return False, 'timeout waiting for service to stop'


def start_mysql_service(service_name: str) -> tuple[bool, str]:
    if is_service_running(service_name):
        return True, 'already running'
    result = subprocess.run(
        ['net', 'start', service_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or '').strip()
        return False, message
    deadline = time.time() + 30
    while time.time() < deadline:
        if is_service_running(service_name):
            time.sleep(1)
            return True, 'started'
        time.sleep(0.5)
    return False, 'timeout waiting for service to start'
