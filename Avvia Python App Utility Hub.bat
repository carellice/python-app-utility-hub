@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHON_BIN=%SCRIPT_DIR%.venv\Scripts\python.exe"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 non trovato. Installalo e riapri Python App Utility Hub.
  pause
  exit /b 1
)

if not exist "%PYTHON_BIN%" (
  echo Creo l'ambiente Python condiviso...
  py -3 -m venv "%SCRIPT_DIR%.venv"
)

"%PYTHON_BIN%" -c "import PIL, mutagen, pypdf, tkinterdnd2" >nul 2>nul
if errorlevel 1 (
  echo Installo le dipendenze necessarie...
  "%PYTHON_BIN%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
  if errorlevel 1 (
    echo Impossibile installare le dipendenze.
    pause
    exit /b 1
  )
)

start "Python App Utility Hub" /b "%PYTHON_BIN%" "%SCRIPT_DIR%utility_launcher.py"
exit /b 0
