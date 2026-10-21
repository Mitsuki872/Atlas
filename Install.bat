@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0Installer.ps1"
if errorlevel 1 echo Installation echouee. Consultez INSTALLATION_WINDOWS.md.
pause
