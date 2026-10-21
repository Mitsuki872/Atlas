@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\windows.ps1" -Action uninstall
pause
