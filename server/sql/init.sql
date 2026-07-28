CREATE DATABASE IF NOT EXISTS vehicle_monitor
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE vehicle_monitor;

CREATE TABLE IF NOT EXISTS device_status (
  device_id        VARCHAR(64)  NOT NULL PRIMARY KEY,
  distance_cm      FLOAT        NOT NULL DEFAULT 0,
  temperature      FLOAT        NOT NULL DEFAULT 0,
  humidity         FLOAT        NOT NULL DEFAULT 0,
  smoke_raw        INT          NOT NULL DEFAULT 0,
  fan              TINYINT(1)   NOT NULL DEFAULT 0,
  alarm            TINYINT(1)   NOT NULL DEFAULT 0,
  window_open      TINYINT(1)   NOT NULL DEFAULT 0,
  auto_mode        TINYINT(1)   NOT NULL DEFAULT 1,
  last_voice_cmd   VARCHAR(128) NOT NULL DEFAULT '',
  wifi_rssi        INT          NOT NULL DEFAULT 0,
  alert_level      VARCHAR(16)  NOT NULL DEFAULT 'ok',
  alerts_json      JSON         NULL,
  updated_at       BIGINT       NOT NULL,
  INDEX idx_device_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备最新状态（每设备仅1行，会被更新；历史请看 sensor_data）';

CREATE TABLE IF NOT EXISTS sensor_data (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id    VARCHAR(64) NOT NULL,
  distance_cm  FLOAT       NOT NULL DEFAULT 0,
  temperature  FLOAT       NOT NULL DEFAULT 0,
  humidity     FLOAT       NOT NULL DEFAULT 0,
  smoke_raw    INT         NOT NULL DEFAULT 0,
  fan          TINYINT(1)  NOT NULL DEFAULT 0,
  alarm        TINYINT(1)  NOT NULL DEFAULT 0,
  window_open  TINYINT(1)  NOT NULL DEFAULT 0,
  auto_mode    TINYINT(1)  NOT NULL DEFAULT 1,
  safety_active TINYINT(1) NOT NULL DEFAULT 1,
  last_voice_cmd VARCHAR(128) NOT NULL DEFAULT '',
  wifi_rssi    INT         NOT NULL DEFAULT 0,
  alert_level  VARCHAR(16) NOT NULL DEFAULT 'ok',
  source       VARCHAR(16) NOT NULL DEFAULT 'http',
  alerts_json  JSON        NULL,
  recorded_at  BIGINT      NOT NULL,
  INDEX idx_sensor_device_time (device_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='传感器与设备状态历史（只增不删）';

CREATE TABLE IF NOT EXISTS alarm_records (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id   VARCHAR(64)  NOT NULL,
  alarm_type  VARCHAR(64)  NOT NULL,
  level       VARCHAR(16)  NOT NULL,
  message     VARCHAR(255) NOT NULL,
  distance_cm FLOAT        NULL,
  temperature FLOAT        NULL,
  humidity    FLOAT        NULL,
  smoke_raw   INT          NULL,
  created_at  BIGINT       NOT NULL,
  INDEX idx_alarm_device_time (device_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报警记录';

CREATE TABLE IF NOT EXISTS remote_operation_records (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id   VARCHAR(64)  NOT NULL,
  action      VARCHAR(32)  NOT NULL,
  value       TINYINT(1)   NOT NULL DEFAULT 1,
  source      VARCHAR(32)  NOT NULL DEFAULT 'web',
  operator    VARCHAR(64)  NOT NULL DEFAULT 'anonymous',
  created_at  BIGINT       NOT NULL,
  INDEX idx_remote_device_time (device_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='远程操作记录';

CREATE TABLE IF NOT EXISTS voice_command_records (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id   VARCHAR(64)  NOT NULL,
  command_text VARCHAR(128) NOT NULL,
  created_at  BIGINT       NOT NULL,
  INDEX idx_voice_device_time (device_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='语音指令记录';

CREATE TABLE IF NOT EXISTS pending_commands (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id   VARCHAR(64) NOT NULL,
  action      VARCHAR(32) NOT NULL,
  value       TINYINT(1)  NOT NULL DEFAULT 1,
  queued_at   BIGINT      NOT NULL,
  INDEX idx_pending_device_time (device_id, queued_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='待下发远程指令队列（只追加不覆盖）';
