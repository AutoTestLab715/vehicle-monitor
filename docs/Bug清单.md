# 车载 IoT 监控系统 — Bug / 改进清单

> 说明：本表用于记录测试过程中发现的问题、复现步骤、修复状态。  
> 状态：`Open` 待修复 | `Fixed` 已修复 | `Won't Fix` 不修复 | `By Design` 设计如此

---

## 已发现并处理

| ID | 模块 | 标题 | 严重级别 | 复现步骤 | 预期 | 实际 | 状态 | 修复说明 |
|----|------|------|----------|----------|------|------|------|----------|
| BUG-001 | 遥测 API | 非法 temperature 类型导致 500 | 中 | POST `/api/telemetry/{id}` body=`{"temperature":"abc"}` | 400 + 错误字段 | 500 Internal Server Error | **Fixed** | 新增 `validation.py`，统一数字校验 |
| BUG-002 | 历史 API | 非法 limit 参数导致 500 | 中 | GET `/api/history/sensors?deviceId=x&limit=bad` | 400 | 500 | **Fixed** | `parse_limit()` 校验 query 参数 |
| BUG-003 | 测试报告 | Allure 双击 index.html 无法加载 | 低 | 直接打开 `allure-report/index.html` | 报告正常 | 500 Failed to fetch | **Fixed** | 改用 `allure open` 本地 HTTP 服务 |
| IMP-001 | 遥测 API | 缺字段自动填 0 | 低 | POST 空 body `{}` | — | 200，字段为 0 | **By Design** | 兼容 ESP32 旧固件，测试已记录 |
| IMP-002 | 遥测 API | 极端值无范围校验 | 低 | humidity=999, distance=-5 | 拒绝或 warn | 200 原样入库 | **Open** | 建议生产环境增加范围校验 |

---

## 待验证 / 待补充（模板）

| ID | 模块 | 标题 | 严重级别 | 复现步骤 | 预期 | 实际 | 状态 | 备注 |
|----|------|------|----------|----------|------|------|------|------|
| BUG-___ | | | 高/中/低 | 1. …<br>2. … | | | Open | |
| BUG-___ | | | | | | | | |
| BUG-___ | | | | | | | | |

---

## 严重级别定义

| 级别 | 说明 | 示例 |
|------|------|------|
| **高** | 核心功能不可用、数据丢失、安全风险 | MySQL 断开无明确错误；控制指令未入库 |
| **中** | 功能异常但有绕行；错误码不合理 | 非法参数 500；报警未写入 alarm_records |
| **低** | UI/体验/边界问题 | 极端值未校验；报告打开方式不直观 |

---

## 缺陷报告模板（复制使用）

```markdown
### BUG-XXX：[简短标题]

- **模块**：
- **严重级别**：高 / 中 / 低
- **环境**：Windows / Flask 3.x / MySQL 8.x / 浏览器 Chrome xxx
- **前置条件**：
- **复现步骤**：
  1.
  2.
- **预期结果**：
- **实际结果**：
- **附件**：截图 / 日志 / 请求响应
- **状态**：Open / Fixed / Won't Fix / By Design
```

---

## 测试→缺陷→修复 闭环示例（面试用）

1. **发现**：异常测试 `temperature="abc"` 返回 500  
2. **分析**：`float()` 未捕获异常，直接抛到 Flask  
3. **修复**：新增 `validation.py`，非法类型返回 400 + `field`  
4. **回归**：更新 pytest 期望为 400，全量 44 条通过  
5. **产出**：Bug 清单 BUG-001 标记 Fixed，Allure 报告留档  

---

## 关联自动化用例

| Bug ID | 对应用例 |
|--------|----------|
| BUG-001 | TC-EXC-004 / test_invalid_temperature_type_returns_400 |
| BUG-002 | TC-EXC-006 / test_history_invalid_limit_returns_400 |
| IMP-001 | TC-EXC-001 ~ TC-EXC-003 |
| IMP-002 | TC-EXC-005 / test_extreme_values_are_stored |
