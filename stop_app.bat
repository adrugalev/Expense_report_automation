@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0local_app.ps1" -Stop
if errorlevel 1 pause

