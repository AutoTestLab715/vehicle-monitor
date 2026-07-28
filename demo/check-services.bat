@echo off

chcp 65001 >nul

title 检查 MySQL 和 MQTT 是否就绪

cd /d "%~dp0..\server"



echo ========================================

echo   检查本机 MySQL + MQTT 连接

echo ========================================

echo.



if not exist "local.env" (

    echo [提示] 尚未配置 server\local.env

    echo 请双击 demo\edit-config.bat 填写 MySQL 密码

    echo.

)



findstr /C:"你的密码" "local.env" >nul 2>&1

if not errorlevel 1 (

    echo [!!] local.env 里还是「你的密码」，请先双击 edit-config.bat 修改

    echo.

)



set MYSQL_OK=0

set MQTT_OK=0



powershell -NoProfile -Command "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',3306); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (

    echo [X] MySQL  127.0.0.1:3306  未连通

    echo     请右键 demo\start-mysql.bat 以管理员身份运行

    echo     或在 services.msc 里启动 MySQL80

) else (

    echo [OK] MySQL  127.0.0.1:3306  端口已监听

    set MYSQL_OK=1

)



powershell -NoProfile -Command "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',1883); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (

    echo [X] MQTT    127.0.0.1:1883  未连通

    echo     请先启动 Mosquitto

) else (

    echo [OK] MQTT    127.0.0.1:1883  端口已监听

    set MQTT_OK=1

)



echo.

if "%MYSQL_OK%"=="0" goto :fail

if "%MQTT_OK%"=="0" goto :fail



echo 基础设施就绪，可以双击 start-server.bat 启动监控后端

echo.

pause

exit /b 0



:fail

echo ----------------------------------------

echo 请先启动 MySQL 和 MQTT，再运行本检查脚本

echo 改配置: 双击 demo\edit-config.bat 编辑 server\local.env

echo ----------------------------------------

echo.

pause

exit /b 1

