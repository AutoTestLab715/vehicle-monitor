@echo off
chcp 65001 >nul
title 打开 Allure 报告

cd /d "%~dp0"

where allure >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 allure 命令: npm install -g allure-commandline
    pause
    exit /b 1
)

if not exist "allure-report\index.html" (
    if exist "allure-results" (
        echo 正在从 allure-results 生成报告...
        allure generate allure-results -o allure-report --clean
    ) else (
        echo [错误] 未找到报告，请先运行 run-allure.bat 或 pytest
        pause
        exit /b 1
    )
)

echo 启动本地服务打开报告（勿直接双击 index.html）...
echo 按 Ctrl+C 停止服务
allure open allure-report
