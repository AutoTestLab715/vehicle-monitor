@echo off

chcp 65001 >nul

title 车载监控系统 - 后端服务 (Flask)

cd /d "%~dp0..\server"



echo ========================================

echo   车载监控系统 - Flask + MySQL + MQTT

echo ========================================

echo.



where python >nul 2>&1

if errorlevel 1 (

    echo [错误] 未检测到 Python 3，请先安装:

    echo   https://www.python.org/downloads/

    echo   安装时勾选 "Add python.exe to PATH"

    echo.

    pause

    exit /b 1

)



if not exist ".venv\" (

    echo 首次运行，正在创建虚拟环境...

    python -m venv .venv

    if errorlevel 1 (

        echo [错误] 创建虚拟环境失败

        pause

        exit /b 1

    )

)



call .venv\Scripts\activate.bat



if not exist ".venv\Lib\site-packages\flask\" (

    echo 正在安装 Python 依赖...

    pip install -r requirements.txt -q

    if errorlevel 1 (

        echo [错误] pip install 失败

        pause

        exit /b 1

    )

    echo.

)



if not exist "local.env" (

    if exist ".env.example" copy /Y ".env.example" "local.env" >nul

)



for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do set PORT_PID=%%a

if defined PORT_PID (

    echo [提示] 端口 3000 已被占用 ^(PID: %PORT_PID%^)

    tasklist /FI "PID eq %PORT_PID%" 2>nul | findstr /i "python.exe node.exe" >nul

    if not errorlevel 1 (

        echo [自动处理] 正在关闭旧服务...

        taskkill /PID %PORT_PID% /F >nul 2>&1

        timeout /t 2 /nobreak >nul

    ) else (

        echo [错误] 端口被其他程序占用

        pause

        exit /b 1

    )

)



echo 正在启动 Flask 服务...

echo.

echo  本机访问:  http://localhost:3000

echo  手机访问:  http://你的电脑IP:3000  （双击 show-ip.bat 查看）

echo.

echo  改 MySQL 密码: 双击 demo\edit-config.bat 编辑 local.env

echo  按 Ctrl+C 可停止服务

echo ========================================

echo.



python run.py



pause

