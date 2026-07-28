# 车载监控系统 - 无硬件演示脚本 (PowerShell)

# 推荐使用 start-demo.bat



$BaseUrl = "http://localhost:3000"

$DeviceId = "vehicle-001"



Write-Host "ESP32 数据模拟 (Python) - 请先运行 start-server.bat" -ForegroundColor Cyan



$serverVenv = Join-Path $PSScriptRoot "..\server\.venv\Scripts\Activate.ps1"

if (Test-Path $serverVenv) {

    . $serverVenv

}



python "$PSScriptRoot\simulate-esp32.py"

