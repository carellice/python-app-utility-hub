@echo off
rem Genera, con un doppio clic, l'installer .exe per Windows x64.
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ====================================================
echo   Python App Utility Hub - generatore Windows
echo ====================================================
echo.
set /p "RELEASE_VERSION=Versione della release [1.0.0]: "
if "%RELEASE_VERSION%"=="" set "RELEASE_VERSION=1.0.0"

set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(sys.version_info ^< (3, 10))" >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3"
)
if defined PYTHON goto python_found

where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys; raise SystemExit(sys.version_info ^< (3, 10))" >nul 2>nul
  if not errorlevel 1 set "PYTHON=python"
)
if defined PYTHON goto python_found

echo.
echo Serve Python 3.10 o successivo per creare l'installer.
echo Installalo da https://www.python.org/downloads/ e riapri questo file.
goto failed

:python_found
echo.
echo Preparo l'ambiente di build...
if not exist ".release-venv\Scripts\python.exe" %PYTHON% -m venv .release-venv
if errorlevel 1 goto failed

call ".release-venv\Scripts\python.exe" -m pip install --upgrade pip -r requirements-build.txt
if errorlevel 1 goto failed

echo.
echo Scarico FFmpeg e FFprobe da includere...
call ".release-venv\Scripts\python.exe" packaging\fetch_ffmpeg.py --output packaging\vendor
if errorlevel 1 goto failed

echo.
echo Creo l'app autosufficiente...
call ".release-venv\Scripts\python.exe" packaging\build.py --output release\app
if errorlevel 1 goto failed
call ".release-venv\Scripts\python.exe" packaging\verify_bundle.py --bundle "release\app\Python App Utility Hub"
if errorlevel 1 goto failed

set "ISCC="
for %%I in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do (
  if exist "%%~fI" set "ISCC=%%~fI"
)
if defined ISCC goto inno_found

echo.
echo Installo automaticamente Inno Setup, necessario per creare il file .exe...
where winget >nul 2>nul
if errorlevel 1 (
  echo Non trovo Windows Package Manager (winget).
  echo Installa Inno Setup 6 da https://jrsoftware.org/isdl.php e riapri questo file.
  goto failed
)
winget install --exact --id JRSoftware.InnoSetup --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto failed
for %%I in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do (
  if exist "%%~fI" set "ISCC=%%~fI"
)
if not defined ISCC (
  echo Non riesco a trovare Inno Setup dopo l'installazione.
  goto failed
)

:inno_found
echo.
echo Creo il pacchetto di installazione...
"%ISCC%" "/DMyAppVersion=%RELEASE_VERSION%" packaging\windows-installer.iss
if errorlevel 1 goto failed

set "INSTALLER=%CD%\release\installers\Python-App-Utility-Hub-Setup-%RELEASE_VERSION%.exe"
echo.
echo Installer creato con successo:
echo %INSTALLER%
explorer.exe /select,"%INSTALLER%"
echo.
pause
exit /b 0

:failed
echo.
echo Creazione dell'installer non riuscita.
pause
exit /b 1
