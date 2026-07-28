-- 已有数据库升级：历史数据只追加、不覆盖旧记录
-- 在 Navicat / MySQL Workbench 中执行；列已存在时的报错可忽略

USE vehicle_monitor;

-- 1) sensor_data 保存完整快照（若某列已存在，跳过对应 ALTER 或忽略 Duplicate column 错误）
ALTER TABLE sensor_data
  ADD COLUMN safety_active TINYINT(1) NOT NULL DEFAULT 1 AFTER auto_mode,
  ADD COLUMN last_voice_cmd VARCHAR(128) NOT NULL DEFAULT '' AFTER safety_active,
  ADD COLUMN wifi_rssi INT NOT NULL DEFAULT 0 AFTER last_voice_cmd,
  ADD COLUMN alert_level VARCHAR(16) NOT NULL DEFAULT 'ok' AFTER wifi_rssi,
  ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'http' AFTER alert_level;

-- 2) pending_commands 改为队列（每条指令独立一行，不再覆盖）
-- 若 pending_commands 已有 id 列，说明已升级，请勿重复执行下面 4 句
CREATE TABLE IF NOT EXISTS pending_commands_new (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(64) NOT NULL,
  action VARCHAR(32) NOT NULL,
  value TINYINT(1) NOT NULL DEFAULT 1,
  queued_at BIGINT NOT NULL,
  INDEX idx_pending_device_time (device_id, queued_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='待下发远程指令队列';

INSERT INTO pending_commands_new (device_id, action, value, queued_at)
SELECT device_id, action, value, queued_at FROM pending_commands;

DROP TABLE pending_commands;
RENAME TABLE pending_commands_new TO pending_commands;
