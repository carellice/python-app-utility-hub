@echo off
setlocal

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%.venv"
set "PYTHON_BIN=%VENV_DIR%\Scripts\python.exe"
set "PYTHONW_BIN=%VENV_DIR%\Scripts\pythonw.exe"

cd /d "%APP_DIR%"

where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_BOOTSTRAP=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python 3 non e' installato o non e' disponibile nel PATH.
    echo Installa Python 3 da https://www.python.org/downloads/windows/ e riapri questo file.
    pause
    exit /b 1
  )
  set "PYTHON_BOOTSTRAP=python"
)

if not exist "%VENV_DIR%" (
  echo Creo l'ambiente Python locale...
  %PYTHON_BOOTSTRAP% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo Impossibile creare l'ambiente Python locale.
    pause
    exit /b 1
  )
)

if not exist "%PYTHON_BIN%" (
  echo L'ambiente Python locale non sembra valido.
  pause
  exit /b 1
)

"%PYTHON_BIN%" -c "import pypdf; import PIL" >nul 2>&1
if errorlevel 1 (
  echo Installo le dipendenze necessarie...
  "%PYTHON_BIN%" -m pip install --upgrade pip
  if errorlevel 1 (
    echo Impossibile aggiornare pip.
    pause
    exit /b 1
  )

  "%PYTHON_BIN%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Impossibile installare le dipendenze.
    pause
    exit /b 1
  )
)

set "APP_PYTHON=%PYTHON_BIN%"
if exist "%PYTHONW_BIN%" set "APP_PYTHON=%PYTHONW_BIN%"

echo Avvio Comic Tag Editor...
start "" /D "%APP_DIR%" "%APP_PYTHON%" "%APP_DIR%comic_tag_editor.py"

endlocal
