@echo off
setlocal
cd /d "%~dp0"

set "BASE_PYTHON="
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "BASE_PYTHON=py -3"
) else (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 set "BASE_PYTHON=python"
)

if "%BASE_PYTHON%"=="" (
  echo Python non trovato. Installa Python 3.10 o superiore da https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creo l'ambiente locale...
  %BASE_PYTHON% -m venv .venv
  if errorlevel 1 (
    echo Impossibile creare l'ambiente locale.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Installo le dipendenze...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Impossibile installare le dipendenze.
    pause
    exit /b 1
  )
)

echo Avvio l'interfaccia grafica...
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "%CD%\gui_app.py"
) else (
  start "" ".venv\Scripts\python.exe" "%CD%\gui_app.py"
)

exit /b 0
