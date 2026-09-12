@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0local_app.ps1"
if errorlevel 1 (
    echo.
    echo The application could not be started. See the message above.
    pause
)

