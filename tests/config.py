import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TESTS_DIR.parent
SERVER_DIR = PROJECT_DIR / 'server'

load_dotenv(SERVER_DIR / '.env')
load_dotenv(SERVER_DIR / 'local.env', override=True)
load_dotenv(TESTS_DIR / '.env.test', override=True)


def _parse_database_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        'host': parsed.hostname or '127.0.0.1',
        'port': parsed.port or 3306,
        'user': unquote(parsed.username or ''),
        'password': unquote(parsed.password or ''),
        'database': (parsed.path or '/vehicle_monitor').lstrip('/').split('?')[0],
    }


_db_url = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://vehicle:vehicle123@127.0.0.1:3306/vehicle_monitor?charset=utf8mb4',
)
_db = _parse_database_url(_db_url)

BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:3000/api').rstrip('/')
DB_HOST = os.getenv('DB_HOST', _db['host'])
DB_PORT = int(os.getenv('DB_PORT', str(_db['port'])))
DB_USER = os.getenv('DB_USER', _db['user'] or 'vehicle')
DB_PASSWORD = os.getenv('DB_PASSWORD', _db['password'] or 'vehicle123')
DB_NAME = os.getenv('DB_NAME', _db['database'] or 'vehicle_monitor')
TEST_DEVICE_PREFIX = os.getenv('TEST_DEVICE_PREFIX', 'pytest-')

MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_COMMAND_PREFIX = os.getenv('MQTT_COMMAND_PREFIX', 'vehicle')
