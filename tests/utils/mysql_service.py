import os
import subprocess
import time

from utils.db_helper import DbHelper

MYSQL_SERVICE = os.getenv('MYSQL_SERVICE', 'MySQL84')


def _run(cmd: str):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def detect_mysql_service() -> str | None:
    for name in (MYSQL_SERVICE, 'MySQL84', 'MySQL80'):
        result = _run(f'sc query {name}')
        if result.returncode == 0:
            return name
    return None


def stop_mysql(service: str) -> tuple[bool, str]:
    result = _run(f'net stop {service}')
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or 'unknown error').strip()
    return True, ''


def start_mysql(service: str) -> tuple[bool, str]:
    result = _run(f'net start {service}')
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or 'unknown error').strip()
    return True, ''


def wait_for_mysql(db_helper: DbHelper, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if db_helper.is_available():
            return True
        time.sleep(0.5)
    return False
