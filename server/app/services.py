import json
import time

from app.extensions import db
from app.models import (
    AlarmRecord,
    DeviceStatus,
    PendingCommand,
    RemoteOperationRecord,
    SensorData,
    VoiceCommandRecord,
)
from app.validation import normalize_telemetry_body


def now_ms():
    return int(time.time() * 1000)


def enrich_alerts(body):
    alerts = body.get('alerts') or {}
    level = 'ok'
    if alerts.get('distanceDanger') or alerts.get('smokeDanger'):
        level = 'danger'
    elif (
        alerts.get('distanceWarn')
        or alerts.get('tempWarn')
        or alerts.get('humidityWarn')
        or alerts.get('smokeWarn')
    ):
        level = 'warn'
    return alerts, level


def _create_alarm_on_transition(device_id, alerts, payload, ts, previous_alerts):
    """报警从「未触发」变为「触发」时写入一条记录，历史只增不删。"""
    previous_alerts = previous_alerts or {}
    mapping = [
        ('distanceDanger', 'distance', 'danger', '碰撞危险：距离过近'),
        ('distanceWarn', 'distance', 'warn', '距离预警：前方障碍物接近'),
        ('smokeDanger', 'smoke', 'danger', '烟雾危险：检测到高浓度烟雾'),
        ('smokeWarn', 'smoke', 'warn', '烟雾预警：烟雾浓度升高'),
        ('tempWarn', 'temperature', 'warn', '温度预警：车内温度过高'),
        ('humidityWarn', 'humidity', 'warn', '湿度预警：车内湿度过高'),
    ]
    for key, alarm_type, level, message in mapping:
        if not alerts.get(key) or previous_alerts.get(key):
            continue
        db.session.add(
            AlarmRecord(
                device_id=device_id,
                alarm_type=alarm_type,
                level=level,
                message=message,
                distance_cm=payload.get('distanceCm'),
                temperature=payload.get('temperature'),
                humidity=payload.get('humidity'),
                smoke_raw=payload.get('smokeRaw'),
                created_at=ts,
            )
        )


def process_telemetry(device_id, body, source='http'):
    ts = now_ms()
    normalized = normalize_telemetry_body(body)
    alerts, alert_level = enrich_alerts(normalized)
    voice_cmd = normalized['lastVoiceCmd']

    payload = {
        'deviceId': device_id,
        'distanceCm': normalized['distanceCm'],
        'temperature': normalized['temperature'],
        'humidity': normalized['humidity'],
        'smokeRaw': normalized['smokeRaw'],
        'fan': normalized['fan'],
        'alarm': normalized['alarm'],
        'windowOpen': normalized['windowOpen'],
        'autoMode': normalized['autoMode'],
        'safetyActive': normalized['safetyActive'],
        'lastVoiceCmd': voice_cmd,
        'wifiRssi': normalized['wifiRssi'],
        'alerts': alerts,
        'alertLevel': alert_level,
        'updatedAt': ts,
        'source': source,
    }

    status = DeviceStatus.query.get(device_id)
    previous_voice = status.last_voice_cmd if status else ''
    previous_alerts = (status.alerts_json or {}) if status else {}
    if not status:
        status = DeviceStatus(device_id=device_id)
        db.session.add(status)

    status.distance_cm = payload['distanceCm']
    status.temperature = payload['temperature']
    status.humidity = payload['humidity']
    status.smoke_raw = payload['smokeRaw']
    status.fan = payload['fan']
    status.alarm = payload['alarm']
    status.window_open = payload['windowOpen']
    status.auto_mode = payload['autoMode']
    status.last_voice_cmd = voice_cmd
    status.wifi_rssi = payload['wifiRssi']
    status.alert_level = alert_level
    status.alerts_json = alerts
    status.updated_at = ts

    db.session.add(
        SensorData(
            device_id=device_id,
            distance_cm=payload['distanceCm'],
            temperature=payload['temperature'],
            humidity=payload['humidity'],
            smoke_raw=payload['smokeRaw'],
            fan=payload['fan'],
            alarm=payload['alarm'],
            window_open=payload['windowOpen'],
            auto_mode=payload['autoMode'],
            safety_active=payload['safetyActive'],
            last_voice_cmd=voice_cmd,
            wifi_rssi=payload['wifiRssi'],
            alert_level=alert_level,
            source=source,
            alerts_json=alerts,
            recorded_at=ts,
        )
    )

    _create_alarm_on_transition(device_id, alerts, payload, ts, previous_alerts)

    if voice_cmd and voice_cmd != previous_voice:
        db.session.add(
            VoiceCommandRecord(
                device_id=device_id,
                command_text=voice_cmd,
                created_at=ts,
            )
        )

    db.session.commit()
    return payload


def queue_command(device_id, action, value=True, source='web', operator='anonymous'):
    ts = now_ms()
    db.session.add(
        PendingCommand(
            device_id=device_id,
            action=action,
            value=bool(value),
            queued_at=ts,
        )
    )

    db.session.add(
        RemoteOperationRecord(
            device_id=device_id,
            action=action,
            value=bool(value),
            source=source,
            operator=operator,
            created_at=ts,
        )
    )
    db.session.commit()
    return {'action': action, 'value': bool(value), 'queuedAt': ts}


def pop_command(device_id):
    cmd = (
        PendingCommand.query.filter_by(device_id=device_id)
        .order_by(PendingCommand.queued_at.asc())
        .first()
    )
    if not cmd:
        return None
    data = cmd.to_dict()
    db.session.delete(cmd)
    db.session.commit()
    return data


def is_online(updated_at, timeout_ms):
    return updated_at and (now_ms() - updated_at) < timeout_ms
