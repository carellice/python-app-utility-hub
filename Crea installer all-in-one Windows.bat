@echo off
rem Pubblica una release GitHub che genera Windows, macOS Intel e macOS Apple Silicon.
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ==========================================================
echo   Python App Utility Hub - release universale GitHub
echo ==========================================================
echo.
echo Questa procedura creera automaticamente gli installer:
echo   - Windows x64 (.exe)
echo   - macOS Intel (.pkg)
echo   - macOS Apple Silicon (.pkg)
echo.
set /p "RELEASE_VERSION=Versione della release [1.0.0]: "
if "%RELEASE_VERSION%"=="" set "RELEASE_VERSION=1.0.0"
if /I "%RELEASE_VERSION:~0,1%"=="v" set "RELEASE_VERSION=%RELEASE_VERSION:~1%"
set "RELEASE_TAG=v%RELEASE_VERSION%"

echo %RELEASE_VERSION% | findstr /r "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo La versione deve avere il formato 1.0.0.
  goto failed
)
where git >nul 2>nul
if errorlevel 1 (
  echo Git non e installato. Installalo da https://git-scm.com/ e riapri questo file.
  goto failed
)

git status --porcelain | findstr . >nul
if not errorlevel 1 (
  echo Ci sono modifiche non salvate in Git. Esegui prima un commit e riapri questo file.
  goto failed
)
for /f "delims=" %%B in ('git branch --show-current') do set "CURRENT_BRANCH=%%B"
if /I not "%CURRENT_BRANCH%"=="main" (
  echo Per pubblicare una release devi trovarti sul branch main.
  goto failed
)
git remote get-url origin >nul 2>nul
if errorlevel 1 (
  echo Non trovo il remoto GitHub "origin".
  goto failed
)

git rev-parse -q --verify "refs/tags/%RELEASE_TAG%" >nul 2>nul
if not errorlevel 1 (
  echo Il tag locale %RELEASE_TAG% esiste gia: scegli un'altra versione.
  goto failed
)

set "TAG_EXISTS="
for /f "delims=" %%T in ('git ls-remote --tags origin refs/tags/%RELEASE_TAG%') do set "TAG_EXISTS=1"
if defined TAG_EXISTS (
  echo Il tag %RELEASE_TAG% esiste gia su GitHub: scegli un'altra versione.
  goto failed
)

echo.
echo Verranno pubblicati il branch main e il tag %RELEASE_TAG% su GitHub.
set /p "CONFIRMATION=Continuare? [s/N]: "
if /I not "%CONFIRMATION%"=="s" (
  echo Operazione annullata.
  pause
  exit /b 0
)

echo.
echo Pubblico il codice necessario...
git push origin main
if errorlevel 1 goto failed
git tag -a "%RELEASE_TAG%" -m "Release %RELEASE_TAG%"
if errorlevel 1 goto failed
git push origin "%RELEASE_TAG%"
if errorlevel 1 goto failed

for /f "delims=" %%U in ('git remote get-url origin') do set "REMOTE_URL=%%U"
set "REPOSITORY_URL=%REMOTE_URL:.git=%"
if /I "%REPOSITORY_URL:~0,15%"=="git@github.com:" set "REPOSITORY_URL=https://github.com/%REPOSITORY_URL:~15%"

echo.
echo Release avviata su GitHub. I tre installer saranno disponibili tra alcuni minuti.
start "" "%REPOSITORY_URL%/actions"
echo.
pause
exit /b 0

:failed
echo.
echo Creazione della release non riuscita.
pause
exit /b 1
