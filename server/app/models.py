from app.extensions import db


class DeviceStatus(db.Model):
    __tablename__ = 'device_status'

    device_id = db.Column(db.String(64), primary_key=True)
    distance_cm = db.Column(db.Float, nullable=False, default=0)
    temperature = db.Column(db.Float, nullable=False, default=0)
    humidity = db.Column(db.Float, nullable=False, default=0)
    smoke_raw = db.Column(db.Integer, nullable=False, default=0)
    fan = db.Column(db.Boolean, nullable=False, default=False)
    alarm = db.Column(db.Boolean, nullable=False, default=False)
    window_open = db.Column(db.Boolean, nullable=False, default=False)
    auto_mode = db.Column(db.Boolean, nullable=False, default=True)
    last_voice_cmd = db.Column(db.String(128), nullable=False, default='')
    wifi_rssi = db.Column(db.Integer, nullable=False, default=0)
    alert_level = db.Column(db.String(16), nullable=False, default='ok')
    alerts_json = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(db.BigInteger, nullable=False)

    def to_dict(self):
        alerts = self.alerts_json or {}
        return {
            'deviceId': self.device_id,
            'distanceCm': self.distance_cm,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'smokeRaw': self.smoke_raw,
            'fan': self.fan,
            'alarm': self.alarm,
            'windowOpen': self.window_open,
            'autoMode': self.auto_mode,
            'lastVoiceCmd': self.last_voice_cmd,
            'wifiRssi': self.wifi_rssi,
            'alerts': alerts,
            'alertLevel': self.alert_level,
            'updatedAt': self.updated_at,
        }


class SensorData(db.Model):
    __tablename__ = 'sensor_data'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    distance_cm = db.Column(db.Float, nullable=False, default=0)
    temperature = db.Column(db.Float, nullable=False, default=0)
    humidity = db.Column(db.Float, nullable=False, default=0)
    smoke_raw = db.Column(db.Integer, nullable=False, default=0)
    fan = db.Column(db.Boolean, nullable=False, default=False)
    alarm = db.Column(db.Boolean, nullable=False, default=False)
    window_open = db.Column(db.Boolean, nullable=False, default=False)
    auto_mode = db.Column(db.Boolean, nullable=False, default=True)
    safety_active = db.Column(db.Boolean, nullable=False, default=True)
    last_voice_cmd = db.Column(db.String(128), nullable=False, default='')
    wifi_rssi = db.Column(db.Integer, nullable=False, default=0)
    alert_level = db.Column(db.String(16), nullable=False, default='ok')
    source = db.Column(db.String(16), nullable=False, default='http')
    alerts_json = db.Column(db.JSON, nullable=True)
    recorded_at = db.Column(db.BigInteger, nullable=False, index=True)


class AlarmRecord(db.Model):
    __tablename__ = 'alarm_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    alarm_type = db.Column(db.String(64), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    distance_cm = db.Column(db.Float, nullable=True)
    temperature = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    smoke_raw = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'deviceId': self.device_id,
            'alarmType': self.alarm_type,
            'level': self.level,
            'message': self.message,
            'distanceCm': self.distance_cm,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'smokeRaw': self.smoke_raw,
            'createdAt': self.created_at,
        }


class RemoteOperationRecord(db.Model):
    __tablename__ = 'remote_operation_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    action = db.Column(db.String(32), nullable=False)
    value = db.Column(db.Boolean, nullable=False, default=True)
    source = db.Column(db.String(32), nullable=False, default='web')
    operator = db.Column(db.String(64), nullable=False, default='anonymous')
    created_at = db.Column(db.BigInteger, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'deviceId': self.device_id,
            'action': self.action,
            'value': self.value,
            'source': self.source,
            'operator': self.operator,
            'createdAt': self.created_at,
        }


class VoiceCommandRecord(db.Model):
    __tablename__ = 'voice_command_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    command_text = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.BigInteger, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'deviceId': self.device_id,
            'commandText': self.command_text,
            'createdAt': self.created_at,
        }


class PendingCommand(db.Model):
    __tablename__ = 'pending_commands'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    action = db.Column(db.String(32), nullable=False)
    value = db.Column(db.Boolean, nullable=False, default=True)
    queued_at = db.Column(db.BigInteger, nullable=False)

    def to_dict(self):
        return {
            'action': self.action,
            'value': self.value,
            'queuedAt': self.queued_at,
        }
