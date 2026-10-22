@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto existing
powershell -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0Installer.ps1"
if errorlevel 1 echo Installation echouee. Consultez INSTALLATION_WINDOWS.md.
pause
exit /b
:existing
echo Mise a jour de Prospect Engine. Les donnees sont conservees.
".venv\Scripts\python.exe" scripts\launcher.py stop
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m app.manage migrate
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\launcher.py start --no-browser
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\launcher.py stop
if errorlevel 1 goto failed
echo Mise a jour terminee. Lancez Start.bat puis Preparez la copie suisse.
pause
exit /b 0
:failed
echo Mise a jour non terminee. Consultez les messages ci-dessus et INSTALLATION_WINDOWS.md.
pause
exit /b 1
