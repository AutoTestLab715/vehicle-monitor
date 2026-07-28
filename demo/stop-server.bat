@echo off
chcp 65001 >nul
title 关闭车载监控服务 (释放 3000 端口)
echo.
echo 正在查找占用 3000 端口的进程...
echo.

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    set FOUND=1
    echo 发现进程 PID: %%a
    tasklist /FI "PID eq %%a"
    echo 正在结束...
    taskkill /PID %%a /F
)

if %FOUND%==0 (
    echo 3000 端口当前未被占用，可以直接启动 start-server.bat
) else (
    echo.
    echo 已释放 3000 端口，现在可以双击 start-server.bat 启动
)

echo.
pause
