@echo off
chcp 65001 >nul
title 车载监控系统 - Allure 测试报告

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 未找到测试虚拟环境，请先运行:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo ========================================
echo   运行 pytest 并生成 Allure 报告
echo ========================================
echo.

pytest %*
set TEST_EXIT=%ERRORLEVEL%

echo.
echo 生成并启动 Allure 报告（本地 HTTP 服务）...

where allure >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 allure 命令，请先安装:
    echo   npm install -g allure-commandline
    pause
    exit /b %TEST_EXIT%
)

allure generate allure-results -o allure-report --clean
if errorlevel 1 (
    echo [错误] allure generate 失败
    pause
    exit /b %TEST_EXIT%
)

echo.
echo [OK] 报告目录: %cd%\allure-report
echo [提示] 请勿直接双击 index.html，将通过 allure open 启动本地服务
echo [提示] 按 Ctrl+C 可停止报告服务
echo.

allure open allure-report

exit /b %TEST_EXIT%
