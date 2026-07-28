# 推送到 GitHub 并启用 CI

## 1. 在 GitHub 创建仓库

1. 打开 https://github.com/new
2. 仓库名建议：`vehicle-monitor`
3. **不要**勾选 "Add a README"（本地已有代码）
4. 创建后复制仓库地址，例如：`https://github.com/你的用户名/vehicle-monitor.git`

## 2. 本地初始化并推送

```powershell
cd D:\ESP32test\vehicle-monitor

git init
git branch -M main
git add .
git status
git commit -m "Add IoT vehicle monitor with pytest automation and CI"
git remote add origin https://github.com/你的用户名/vehicle-monitor.git
git push -u origin main
```

## 3. 查看 CI 运行结果

推送后打开 GitHub 仓库 → **Actions** 标签页，应看到 **CI** workflow 自动运行。

预期结果：
- ✅ Start MySQL and MQTT（docker compose）
- ✅ Run pytest（44 条，排除 fault）
- ✅ Upload Allure results（Artifacts 可下载）

## 4. 下载 Allure 报告（CI 产物）

Actions → 某次运行 → Artifacts → 下载 `allure-results`  
本地生成 HTML：

```powershell
allure generate allure-results -o allure-report --clean
allure open allure-report
```

## 5. 常见问题

| 问题 | 处理 |
|------|------|
| CI 中 MySQL 连接失败 | 检查 docker compose 健康检查等待时间 |
| Mosquitto 启动失败 | 确认 `infra/mosquitto/mosquitto.conf` 已提交 |
| push 被拒绝 | 先 `git pull origin main --rebase` 再 push |
| 含敏感信息 | `server/local.env` 已在 .gitignore，勿提交密码 |

## 6. 可选：安装 GitHub CLI

```powershell
winget install GitHub.cli
gh auth login
gh repo create vehicle-monitor --public --source=. --push
```
