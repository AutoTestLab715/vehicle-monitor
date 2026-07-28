# Postman 接口集合

## 导入步骤

1. 打开 Postman → **Import**
2. 选择以下两个文件：
   - `vehicle-monitor.postman_collection.json`
   - `Local.postman_environment.json`
3. 右上角环境切换为 **Local 本地开发**
4. 确保 Flask 后端已启动：`http://127.0.0.1:3000`

## 目录结构

| 文件夹 | 接口数 | 对应 pytest 模块 |
|--------|--------|------------------|
| 01-冒烟测试 | 3 | test_health.py |
| 02-遥测上报 | 5 | test_telemetry.py / test_exception.py |
| 03-远程控制 | 5 | test_control.py |
| 04-报警与日志 | 3 | test_alarm.py |
| 05-历史数据 | 4 | test_history.py |

## 建议测试顺序

```text
Health → Post Telemetry 正常 → Get Device → Control Fan → Poll Commands → List Alarms → Sensor History
```

## 异常场景快速验证

- **Post Telemetry 非法温度** → 期望 400
- **Control 非法 action** → 期望 400 + validActions
- **Sensor History 非法 limit** → 期望 400
