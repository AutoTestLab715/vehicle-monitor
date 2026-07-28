import copy
import json
import os
import uuid
from datetime import datetime

import allure
import pytest

from config import (
    BASE_URL,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    MQTT_BROKER,
    MQTT_COMMAND_PREFIX,
    MQTT_PORT,
    TEST_DEVICE_PREFIX,
)
from utils.api_client import ApiClient
from utils.db_helper import DbHelper
from utils.mqtt_helper import MqttHelper
from utils.mysql_service import detect_mysql_service, start_mysql, stop_mysql, wait_for_mysql

ALLURE_RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'allure-results')
ALLURE_EPIC = '车载 IoT 监控系统'

MARKER_FEATURES = {
    'smoke': '冒烟测试',
    'telemetry': '遥测上报',
    'control': '远程控制',
    'alarm': '报警联动',
    'history': '历史数据',
    'mqtt': 'MQTT 通信',
    'websocket': 'WebSocket 实时推送',
    'exception': '异常场景',
    'fault': '故障注入',
}


def pytest_addoption(parser):
    parser.addoption(
        '--run-fault-tests',
        action='store_true',
        default=False,
        help='运行破坏性故障测试（如短暂停止 MySQL 服务）',
    )


def pytest_sessionstart(session):
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
    env_file = os.path.join(ALLURE_RESULTS_DIR, 'environment.properties')
    with open(env_file, 'w', encoding='utf-8') as fh:
        fh.write(f'API_BASE_URL={BASE_URL}\n')
        fh.write(f'DB_HOST={DB_HOST}\n')
        fh.write(f'DB_PORT={DB_PORT}\n')
        fh.write(f'DB_NAME={DB_NAME}\n')
        fh.write(f'MQTT_BROKER={MQTT_BROKER}\n')
        fh.write(f'MQTT_PORT={MQTT_PORT}\n')
        fh.write(f'Run.At={datetime.now().isoformat(timespec="seconds")}\n')


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f'rep_{rep.when}', rep)


@pytest.fixture(autouse=True)
def allure_report_context(request, api_client):
    allure.dynamic.epic(ALLURE_EPIC)
    for marker, feature in MARKER_FEATURES.items():
        if request.node.get_closest_marker(marker):
            allure.dynamic.feature(feature)
            allure.dynamic.tag(marker)
            break

    device_id = getattr(request, 'param', None)
    if isinstance(device_id, str) and device_id.startswith(TEST_DEVICE_PREFIX):
        allure.dynamic.parameter('deviceId', device_id)

    yield

    rep = getattr(request.node, 'rep_call', None)
    if rep is not None and rep.failed and api_client.last_response is not None:
        resp = api_client.last_response
        body = resp.text
        try:
            body = json.dumps(resp.json(), ensure_ascii=False, indent=2)
        except ValueError:
            pass
        allure.attach(
            f'URL: {resp.request.method} {resp.url}\n'
            f'Status: {resp.status_code}\n\n{body}',
            name='最后一次 API 响应',
            attachment_type=allure.attachment_type.TEXT,
        )


@pytest.fixture
def mysql_stopped(request, db_helper):
    if not request.config.getoption('--run-fault-tests'):
        pytest.skip('MySQL 故障测试需加参数: pytest --run-fault-tests -m fault')

    service = detect_mysql_service()
    if not service:
        pytest.skip('未检测到 MySQL Windows 服务 (MySQL84/MySQL80)')

    ok, err = stop_mysql(service)
    if not ok:
        pytest.skip(f'无法停止 {service}（可能需要管理员权限）: {err}')

    try:
        yield service
    finally:
        started, start_err = start_mysql(service)
        if not started:
            pytest.fail(f'测试后无法重启 {service}: {start_err}')
        if not wait_for_mysql(db_helper):
            pytest.fail(f'{service} 已重启但数据库仍不可连接')


@pytest.fixture
def bad_db_helper():
    return DbHelper(DB_HOST, DB_PORT, DB_USER, 'wrong-password', DB_NAME)


NORMAL_TELEMETRY = {
    'distanceCm': 45.2,
    'temperature': 26.5,
    'humidity': 55,
    'smokeRaw': 650,
    'fan': False,
    'alarm': False,
    'windowOpen': False,
    'autoMode': True,
    'safetyActive': True,
    'lastVoiceCmd': '',
    'wifiRssi': -58,
    'alerts': {
        'distanceWarn': False,
        'distanceDanger': False,
        'tempWarn': False,
        'humidityWarn': False,
        'smokeWarn': False,
        'smokeDanger': False,
    },
}


def make_telemetry(**overrides):
    payload = copy.deepcopy(NORMAL_TELEMETRY)
    alerts = overrides.pop('alerts', None)
    if alerts is not None:
        payload['alerts'] = {**payload['alerts'], **alerts}
    payload.update(overrides)
    return payload


DANGER_TELEMETRY = {
    'distanceCm': 12,
    'temperature': 37.5,
    'humidity': 82,
    'smokeRaw': 2900,
    'fan': True,
    'alarm': True,
    'windowOpen': True,
    'autoMode': True,
    'safetyActive': True,
    'lastVoiceCmd': '开风扇',
    'wifiRssi': -62,
    'alerts': {
        'distanceWarn': True,
        'distanceDanger': True,
        'tempWarn': True,
        'humidityWarn': True,
        'smokeWarn': True,
        'smokeDanger': True,
    },
}


@pytest.fixture(scope='session')
def api_client():
    return ApiClient(BASE_URL)


@pytest.fixture(scope='session')
def db_helper():
    return DbHelper(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)


@pytest.fixture(scope='session')
def require_api(api_client):
    if not api_client.is_available():
        pytest.skip(f'Flask API 不可用，请先启动服务: {BASE_URL}/health')
    return api_client


@pytest.fixture(scope='session')
def require_db(db_helper):
    if not db_helper.is_available():
        pytest.skip(
            f'MySQL 不可用，请先启动数据库 ({DB_HOST}:{DB_PORT}/{DB_NAME})'
        )
    return db_helper


@pytest.fixture(scope='session')
def mqtt_helper():
    return MqttHelper(MQTT_BROKER, MQTT_PORT, MQTT_COMMAND_PREFIX)


@pytest.fixture(scope='session')
def require_mqtt(mqtt_helper):
    if not mqtt_helper.is_available():
        pytest.skip(f'MQTT Broker 不可用，请先启动: {MQTT_BROKER}:{MQTT_PORT}')
    return mqtt_helper


@pytest.fixture
def test_device_id():
    return f'{TEST_DEVICE_PREFIX}{uuid.uuid4().hex[:8]}'


@pytest.fixture
def clean_device(require_db, test_device_id):
    require_db.cleanup_device(test_device_id)
    yield test_device_id
    require_db.cleanup_device(test_device_id)


@pytest.fixture
def normal_telemetry():
    return copy.deepcopy(NORMAL_TELEMETRY)


@pytest.fixture
def danger_telemetry():
    return copy.deepcopy(DANGER_TELEMETRY)


@pytest.fixture
def registered_device(require_api, clean_device, normal_telemetry):
    device_id = clean_device
    require_api.post_telemetry(device_id, normal_telemetry)
    return device_id
