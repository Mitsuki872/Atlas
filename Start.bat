@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Lancez Install.bat pour installer Python et les dependances.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" scripts\launcher.py start
if errorlevel 1 pause
