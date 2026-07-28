# ESP32 车载辅助监控系统

一体化车载监控方案：ESP32 采集距离/温湿度/烟雾，驱动风扇/声光警报/车窗，支持按键与语音本地控制，并通过 **MQTT / HTTP** 将数据同步至 **Flask 后端 + MySQL**，Web/手机端通过 **REST + WebSocket** 实时查看与远程操控。

## 系统架构（与技术架构图对齐）

```
┌──────────────────────────────────────────────────────────────────┐
│                         ESP32 主控                                │
│  传感器: HC-SR04 | DHT22 | MQ-2 | 按键 | 语音模块(Serial)          │
│  执行器: 继电器(风扇) | 蜂鸣器+LED | 舵机(车窗)                    │
│  逻辑: 安全联动(最高优先级) + 本地/远程控制 + 离线缓冲             │
└───────────────┬──────────────────────────────┬───────────────────┘
                │ MQTT (主)                     │ HTTP (备用)
                ▼                               ▼
┌───────────────────────────┐      ┌───────────────────────────────┐
│   MQTT Broker (Mosquitto) │      │   Flask 后端 (REST + SocketIO) │
│   vehicle/{id}/telemetry  │◄────►│   遥测入库 / 指令下发 / 实时推送 │
│   vehicle/{id}/commands   │      └───────────────┬───────────────┘
└───────────────────────────┘                      │
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │         MySQL 数据库          │
                                    │  sensor_data / device_status   │
                                    │  alarm_records                 │
                                    │  remote_operation_records      │
                                    │  voice_command_records         │
                                    └───────────────┬──────────────┘
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                        电脑浏览器                                   手机浏览器
                     http://服务器IP:3000                    (响应式 + PWA)
```

## 目录结构

```
vehicle-monitor/
├── esp32-firmware/          # ESP32 Arduino 固件 (MQTT + HTTP)
│   ├── VehicleMonitor/
│   │   └── VehicleMonitor.ino
│   └── config.h
├── server/                  # Flask 后端
│   ├── run.py               # 启动入口
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py      # 应用工厂 + SocketIO
│   │   ├── routes.py        # REST API
│   │   ├── mqtt_handler.py  # MQTT 订阅/发布
│   │   ├── models.py        # ORM 模型
│   │   └── services.py      # 业务逻辑
│   ├── sql/init.sql         # MySQL 建表脚本
│   └── src/index.js         # [已弃用] 旧 Node.js 版
├── web/                     # Web / 手机前端
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── infra/mosquitto/         # MQTT Broker 配置
├── docker-compose.yml       # MySQL + Mosquitto
├── demo/                    # Windows 演示脚本
│   ├── start-infra.bat      # 启动 MySQL + MQTT
│   ├── start-server.bat     # 启动 Flask
│   ├── start-demo.bat       # 模拟 ESP32 数据
│   └── simulate-esp32.py
├── WINDOWS.md
└── README.md
```

## 快速开始

### 1. 启动基础设施（MySQL + MQTT）

需要安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

```bash
cd vehicle-monitor
docker compose up -d
```

或 Windows 双击 `demo\start-infra.bat`。

| 服务 | 地址 | 账号 |
|------|------|------|
| MySQL | `127.0.0.1:3306` | `vehicle` / `vehicle123` |
| MQTT | `127.0.0.1:1883` | 匿名 |

### 2. 启动 Flask 后端

```bash
cd vehicle-monitor/server
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env        # Windows
python run.py
```

或 Windows 双击 `demo\start-server.bat`。

访问：<http://localhost:3000>

### 3. 无硬件演示

```bash
cd vehicle-monitor/demo
python simulate-esp32.py
```

或双击 `demo\start-demo.bat`。

### 4. 配置并烧录 ESP32

编辑 `esp32-firmware/config.h`，打开 `esp32-firmware/VehicleMonitor/VehicleMonitor.ino` 烧录：

```cpp
#define WIFI_SSID       "你的WiFi"
#define WIFI_PASSWORD   "你的WiFi密码"
#define SERVER_HOST     "192.168.1.100"   // Flask 服务器 IP
#define MQTT_BROKER     "192.168.1.100"   // MQTT Broker IP
#define DEVICE_ID       "vehicle-001"
```

依赖库：DHT sensor library、ArduinoJson、ESP32Servo、**PubSubClient**。

## API 说明

### ESP32 → 服务器

**MQTT 上报** `vehicle/{deviceId}/telemetry`（JSON，与 HTTP 体相同）

**HTTP 上报** `POST /api/telemetry/:deviceId`

**HTTP 拉取指令** `GET /api/commands/:deviceId`（MQTT 不可用时）

**MQTT 接收指令** `vehicle/{deviceId}/commands`

### Web / 手机 → 服务器

| 接口 | 说明 |
|------|------|
| `GET /api/devices` | 设备列表 |
| `GET /api/devices/:id` | 设备状态 |
| `POST /api/devices/:id/control` | 远程控制 |
| `GET /api/alarms` | 报警记录 |
| `GET /api/operations` | 远程操作记录 |
| `GET /api/voice-commands` | 语音指令记录 |
| `GET /api/history/sensors` | 传感器历史 |
| WebSocket | Flask-SocketIO 实时推送 `telemetry` |

控制 action：`fan` / `alarm` / `window` / `toggleFan` / `toggleAlarm` / `toggleWindow`

**控制逻辑**：不再区分手动/自动模式。Web/手机/按键/语音可随时开关执行器；ESP32 端安全机制始终运行，危险时自动联动。若用户手动关闭某执行器，约 **1 秒**内不强制；1 秒后若传感器仍处危险状态，安全机制会重新触发（如高温时风扇再次打开）。

## 数据库表

| 表名 | 用途 | 写入方式 |
|------|------|----------|
| `device_status` | 设备**最新**状态（供 Web 实时展示） | 按设备更新一条 |
| `sensor_data` | 传感器与执行器**完整历史** | **每次上报追加一条，不覆盖** |
| `alarm_records` | 报警记录 | **触发时追加，不覆盖** |
| `remote_operation_records` | 远程操作记录 | **每次操作追加，不覆盖** |
| `voice_command_records` | 语音指令记录 | **新指令追加，不覆盖** |
| `pending_commands` | 待下发 HTTP 指令队列 | **排队追加，逐条下发后删除** |

> 若你之前已建过库，请执行一次升级脚本以启用完整历史字段与指令队列：  
> `server/sql/migrate_preserve_history.sql`（或在 Navicat 中打开运行）

## 常见问题

**Q: Web 显示离线？**  
确认 ESP32 与服务器同一 WiFi；`config.h` 中 IP 为局域网地址；防火墙放行 3000/1883 端口。

**Q: Flask 启动报 MySQL 连接失败？**  
先运行 `docker compose up -d` 或 `start-infra.bat`，等待约 15 秒后再启动 Flask。

**Q: MQTT 不可用？**  
ESP32 会自动降级为 HTTP 上报 + 轮询指令；离线数据会缓存在设备端（最多 5 条）。

**Q: 旧 Node.js 版还能用吗？**  
`server/src/index.js` 已弃用，无 MySQL/MQTT/日志持久化，仅作参考。

## 许可证

MIT — 课程/实训项目可自由修改使用。
