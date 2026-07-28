import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR.parent / 'web'

load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / 'local.env', override=True)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'vehicle-monitor-dev-key')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://vehicle:vehicle123@127.0.0.1:3306/vehicle_monitor?charset=utf8mb4',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
    MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
    MQTT_TELEMETRY_TOPIC = os.getenv('MQTT_TELEMETRY_TOPIC', 'vehicle/+/telemetry')
    MQTT_COMMAND_PREFIX = os.getenv('MQTT_COMMAND_PREFIX', 'vehicle')

    VALID_ACTIONS = {
        'fan', 'alarm', 'window',
        'toggleFan', 'toggleAlarm', 'toggleWindow',
    }

    ONLINE_TIMEOUT_MS = int(os.getenv('ONLINE_TIMEOUT_MS', '10000'))
