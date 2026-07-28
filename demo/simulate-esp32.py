#!/usr/bin/env python3
"""ESP32 数据模拟 - 无硬件电脑演示（HTTP + 可选 MQTT）"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

BASE_URL = os.getenv('SERVER_URL', 'http://localhost:3000')
DEVICE_ID = os.getenv('DEVICE_ID', 'vehicle-001')
INTERVAL_MS = int(os.getenv('INTERVAL_MS', '4000'))
USE_MQTT = os.getenv('USE_MQTT', '1') == '1'
MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
SAFETY_OVERRIDE_SEC = 1.0

actuator_state = {
    'fan': False,
    'alarm': False,
    'windowOpen': False,
    'lastVoiceCmd': '',
}

safety_block_until = {
    'fan': 0.0,
    'alarm': 0.0,
    'window': 0.0,
}

SCENARIOS = [
    {
        'name': '正常行驶',
        'data': {
            'distanceCm': 80, 'temperature': 26, 'humidity': 55, 'smokeRaw': 600,
            'alerts': {
                'distanceWarn': False, 'distanceDanger': False,
                'tempWarn': False, 'humidityWarn': False,
                'smokeWarn': False, 'smokeDanger': False,
            },
        },
    },
    {
        'name': '距离预警 - 接近障碍物',
        'data': {
            'distanceCm': 28, 'temperature': 26, 'humidity': 55, 'smokeRaw': 600,
            'alerts': {
                'distanceWarn': True, 'distanceDanger': False,
                'tempWarn': False, 'humidityWarn': False,
                'smokeWarn': False, 'smokeDanger': False,
            },
        },
    },
    {
        'name': '碰撞危险 - 距离过近',
        'data': {
            'distanceCm': 12, 'temperature': 26, 'humidity': 55, 'smokeRaw': 600,
            'alerts': {
                'distanceWarn': True, 'distanceDanger': True,
                'tempWarn': False, 'humidityWarn': False,
                'smokeWarn': False, 'smokeDanger': False,
            },
        },
    },
    {
        'name': '温度过高 - 自动开风扇',
        'data': {
            'distanceCm': 80, 'temperature': 37, 'humidity': 65, 'smokeRaw': 700,
            'alerts': {
                'distanceWarn': False, 'distanceDanger': False,
                'tempWarn': True, 'humidityWarn': False,
                'smokeWarn': False, 'smokeDanger': False,
            },
        },
    },
    {
        'name': '烟雾危险 - 自动开窗',
        'data': {
            'distanceCm': 80, 'temperature': 30, 'humidity': 60, 'smokeRaw': 2900,
            'alerts': {
                'distanceWarn': False, 'distanceDanger': False,
                'tempWarn': False, 'humidityWarn': False,
                'smokeWarn': True, 'smokeDanger': True,
            },
        },
    },
    {
        'name': '恢复正常',
        'data': {
            'distanceCm': 100, 'temperature': 25, 'humidity': 50, 'smokeRaw': 500,
            'alerts': {
                'distanceWarn': False, 'distanceDanger': False,
                'tempWarn': False, 'humidityWarn': False,
                'smokeWarn': False, 'smokeDanger': False,
            },
        },
    },
]


def http_request(method, path, body=None):
    url = f'{BASE_URL}{path}'
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={'Content-Type': 'application/json'} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode('utf-8', errors='ignore')


def apply_command(cmd):
    action = cmd.get('action')
    value = cmd.get('value', True)
    now = time.time()
    if action == 'fan':
        actuator_state['fan'] = bool(value)
        if not value:
            safety_block_until['fan'] = now + SAFETY_OVERRIDE_SEC
    elif action == 'alarm':
        actuator_state['alarm'] = bool(value)
        if not value:
            safety_block_until['alarm'] = now + SAFETY_OVERRIDE_SEC
    elif action == 'window':
        actuator_state['windowOpen'] = bool(value)
        if not value:
            safety_block_until['window'] = now + SAFETY_OVERRIDE_SEC
    elif action == 'toggleFan':
        actuator_state['fan'] = not actuator_state['fan']
        if not actuator_state['fan']:
            safety_block_until['fan'] = now + SAFETY_OVERRIDE_SEC
    elif action == 'toggleAlarm':
        actuator_state['alarm'] = not actuator_state['alarm']
        if not actuator_state['alarm']:
            safety_block_until['alarm'] = now + SAFETY_OVERRIDE_SEC
    elif action == 'toggleWindow':
        actuator_state['windowOpen'] = not actuator_state['windowOpen']
        if not actuator_state['windowOpen']:
            safety_block_until['window'] = now + SAFETY_OVERRIDE_SEC


def apply_safety(scene):
    alerts = scene['data'].get('alerts', {})
    now = time.time()
    danger = alerts.get('distanceDanger') or alerts.get('smokeDanger')
    warn = alerts.get('distanceWarn') or alerts.get('tempWarn') or alerts.get('humidityWarn') or alerts.get('smokeWarn')

    need_fan = danger or alerts.get('tempWarn')
    need_alarm = danger or warn
    need_window = alerts.get('smokeDanger')

    if need_fan and now >= safety_block_until['fan']:
        actuator_state['fan'] = True
    elif not need_fan and now >= safety_block_until['fan']:
        actuator_state['fan'] = False

    if need_alarm and now >= safety_block_until['alarm']:
        actuator_state['alarm'] = True
    elif not need_alarm and not warn and now >= safety_block_until['alarm']:
        actuator_state['alarm'] = False

    if need_window and now >= safety_block_until['window']:
        actuator_state['windowOpen'] = True
    elif not need_window and now >= safety_block_until['window']:
        actuator_state['windowOpen'] = False


def merge_scenario(scene):
    apply_safety(scene)
    payload = {
        **scene['data'],
        'deviceId': DEVICE_ID,
        'fan': actuator_state['fan'],
        'alarm': actuator_state['alarm'],
        'windowOpen': actuator_state['windowOpen'],
        'autoMode': True,
        'safetyActive': True,
        'lastVoiceCmd': actuator_state['lastVoiceCmd'],
        'wifiRssi': -55,
    }
    return payload


def post_telemetry_http(payload):
    status, body = http_request('POST', f'/api/telemetry/{DEVICE_ID}', payload)
    if status != 200:
        raise RuntimeError(f'HTTP {status}: {body}')


def poll_commands_http():
    status, body = http_request('GET', f'/api/commands/{DEVICE_ID}')
    if status == 200 and body:
        try:
            apply_command(json.loads(body))
            print(f'  [远程指令 HTTP] {body}')
        except json.JSONDecodeError:
            pass


class MqttSim:
    def __init__(self):
        self.client = None
        self.connected = False

    def start(self):
        if not mqtt or not USE_MQTT:
            return
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        rc = getattr(reason_code, 'value', reason_code)
        if rc == 0:
            self.connected = True
            client.subscribe(f'vehicle/{DEVICE_ID}/commands')

    def _on_message(self, client, userdata, msg):
        apply_command(json.loads(msg.payload.decode('utf-8')))
        print(f'  [远程指令 MQTT] {msg.payload.decode("utf-8")}')

    def publish(self, payload):
        if self.client and self.connected:
            topic = f'vehicle/{DEVICE_ID}/telemetry'
            self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)


def main():
    print('========================================')
    print('  ESP32 数据模拟 (Flask 架构版)')
    print('  请先启动: start-server.bat')
    print(f'  浏览器: {BASE_URL}')
    print('========================================\n')

    mqtt_sim = MqttSim()
    mqtt_sim.start()

    round_no = 0
    while True:
        round_no += 1
        for scene in SCENARIOS:
            try:
                poll_commands_http()
                payload = merge_scenario(scene)
                if mqtt_sim.connected:
                    mqtt_sim.publish(payload)
                else:
                    post_telemetry_http(payload)
                ts = time.strftime('%H:%M:%S')
                print(f'[{ts}] 场景: {scene["name"]}')
                print(
                    f'  距离={payload["distanceCm"]}cm  温度={payload["temperature"]}C  '
                    f'烟雾={payload["smokeRaw"]}'
                )
                print(
                    f'  风扇={"开" if payload["fan"] else "关"}  '
                    f'警报={"开" if payload["alarm"] else "关"}  '
                    f'车窗={"开" if payload["windowOpen"] else "关"}'
                )
            except Exception as exc:
                print('\n[错误] 无法连接后端，请先启动 start-server.bat 和 docker-compose')
                print('详情:', exc)
                sys.exit(1)
            time.sleep(INTERVAL_MS / 1000)
        print(f'\n--- 第 {round_no} 轮演示完成，循环播放 ---\n')


if __name__ == '__main__':
    main()
