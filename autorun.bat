chcp  65001 1>nul 2>nul
@rem
@echo off

color FF
title oas Updater



:: 检查管理员权限
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

:: 如果返回值不等于 0，则重新启动脚本以获取管理员权限
if %errorlevel% neq 0 (
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

cd /d "%~dp0"
set "_root=%~dp0"
set "_root=%_root:~0,-1%"
cd "%_root%"
echo "%_root%

set "_pyBin=%_root%\toolkit"
set "_GitBin=%_root%\toolkit\Git\mingw64\bin"
set "_adbBin=%_root%\toolkit\Lib\site-packages\adbutils\binaries"
set "PATH=%_root%\toolkit\alias;%_root%\toolkit\command;%_pyBin%;%_pyBin%\Scripts;%_GitBin%;%_adbBin%;%PATH%"


 
start /b python server.py
start /b python my_start.py oas2
 
:: 获取 my_start.py 的进程ID并等待5秒后终止
for /f "tokens=2" %%i in ('tasklist ^| findstr python.exe') do set pid=%%i
timeout /t 3000 >nul
taskkill /F /PID %pid% >nul
