"""启动时自动补齐数据库结构，避免 MQTT/HTTP 入库失败。"""

from sqlalchemy import inspect, text

from app.extensions import db


def _column_exists(inspector, table, column):
    return column in {c['name'] for c in inspector.get_columns(table)}


def _table_exists(inspector, table):
    return table in inspector.get_table_names()


def ensure_schema():
    inspector = inspect(db.engine)

    if _table_exists(inspector, 'sensor_data'):
        alters = []
        if not _column_exists(inspector, 'sensor_data', 'safety_active'):
            alters.append(
                'ADD COLUMN safety_active TINYINT(1) NOT NULL DEFAULT 1 AFTER auto_mode'
            )
        if not _column_exists(inspector, 'sensor_data', 'last_voice_cmd'):
            alters.append(
                "ADD COLUMN last_voice_cmd VARCHAR(128) NOT NULL DEFAULT '' AFTER safety_active"
            )
        if not _column_exists(inspector, 'sensor_data', 'wifi_rssi'):
            alters.append(
                'ADD COLUMN wifi_rssi INT NOT NULL DEFAULT 0 AFTER last_voice_cmd'
            )
        if not _column_exists(inspector, 'sensor_data', 'alert_level'):
            alters.append(
                "ADD COLUMN alert_level VARCHAR(16) NOT NULL DEFAULT 'ok' AFTER wifi_rssi"
            )
        if not _column_exists(inspector, 'sensor_data', 'source'):
            alters.append(
                "ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'http' AFTER alert_level"
            )
        if alters:
            db.session.execute(text(f"ALTER TABLE sensor_data {', '.join(alters)}"))
            db.session.commit()
            print(f'[DB] sensor_data upgraded ({len(alters)} columns)')

    if _table_exists(inspector, 'pending_commands'):
        inspector = inspect(db.engine)
        if not _column_exists(inspector, 'pending_commands', 'id'):
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pending_commands_new (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  device_id VARCHAR(64) NOT NULL,
                  action VARCHAR(32) NOT NULL,
                  value TINYINT(1) NOT NULL DEFAULT 1,
                  queued_at BIGINT NOT NULL,
                  INDEX idx_pending_device_time (device_id, queued_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            db.session.execute(text("""
                INSERT INTO pending_commands_new (device_id, action, value, queued_at)
                SELECT device_id, action, value, queued_at FROM pending_commands
            """))
            db.session.execute(text('DROP TABLE pending_commands'))
            db.session.execute(text('RENAME TABLE pending_commands_new TO pending_commands'))
            db.session.commit()
            print('[DB] pending_commands upgraded to queue mode')
