@echo off
chcp 65001 >nul
title 启动 MySQL 服务
echo ========================================
echo   启动 MySQL Windows 服务
echo   支持 MySQL84 / MySQL80
echo ========================================
echo.

set SVC=
sc query MySQL84 >nul 2>&1
if not errorlevel 1 set SVC=MySQL84
if "%SVC%"=="" (
    sc query MySQL80 >nul 2>&1
    if not errorlevel 1 set SVC=MySQL80
)

if "%SVC%"=="" (
    echo [错误] 未找到 MySQL84 或 MySQL80 服务
    echo 请先安装 MySQL: D:\mysql\安装MySQL84到D盘.bat
    pause
    exit /b 1
)

echo 检测到服务: %SVC%

sc query %SVC% | findstr /C:"RUNNING" >nul
if not errorlevel 1 (
    echo [OK] %SVC% 已在运行
    goto :done
)

echo 正在启动 %SVC% ...
net start %SVC%
if errorlevel 1 (
    echo.
    echo [失败] 请右键本文件 -^> 以管理员身份运行
    echo 或在 services.msc 里手动启动 %SVC%
    pause
    exit /b 1
)

:done
echo.
echo [OK] MySQL 已启动 (3306)
echo 下一步: init-database.bat 或 Navicat 运行 init.sql
echo.
pause
