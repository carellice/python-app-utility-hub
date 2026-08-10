@echo off
cd /d "%~dp0"
set "SCRIPT=%~dp0extract_audio_tracks.py"

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%SCRIPT%"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%SCRIPT%"
    exit /b 0
)

start "" py -3 "%SCRIPT%"
exit /b 0
