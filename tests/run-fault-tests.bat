@echo off
chcp 65001 >nul
title 车载监控系统 - MySQL 故障测试

cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
    echo [错误] 请右键本文件，选择「以管理员身份运行」
    echo.
    echo MySQL 故障测试需要执行 net stop / net start，普通终端无权限。
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 未找到测试虚拟环境，请先运行:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo ========================================
echo   MySQL 故障注入测试
echo   将短暂停止 MySQL 并验证 API 返回 500
echo ========================================
echo.
echo [提示] 请确保 Flask 后端已启动: http://127.0.0.1:3000
echo [提示] 测试结束后会自动重启 MySQL 服务
echo.

pytest -m fault --run-fault-tests -v
set TEST_EXIT=%ERRORLEVEL%

echo.
if %TEST_EXIT%==0 (
    echo [OK] MySQL 故障测试全部通过
) else (
    echo [完成] 测试结束，请查看上方输出
    echo 若 MySQL 未自动恢复，请手动执行: net start MySQL84
)

echo.
pause
exit /b %TEST_EXIT%
