@echo off
chcp 65001 >nul
title 推送到 GitHub

cd /d "%~dp0"

if not exist ".git" (
    echo [错误] 未找到 git 仓库
    pause
    exit /b 1
)

set /p REPO_URL=请输入 GitHub 仓库地址 (例: https://github.com/user/vehicle-monitor.git): 
if "%REPO_URL%"=="" (
    echo [错误] 地址不能为空
    pause
    exit /b 1
)

git remote remove origin 2>nul
git remote add origin "%REPO_URL%"
git push -u origin main

if errorlevel 1 (
    echo.
    echo [失败] 推送失败，请确认:
    echo   1. 已在 GitHub 创建空仓库
    echo   2. 已登录 git 凭据管理器
    echo   3. 仓库地址正确
    pause
    exit /b 1
)

echo.
echo [OK] 推送成功！请到 GitHub 仓库 Actions 页查看 CI 运行结果。
pause
