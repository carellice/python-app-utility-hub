@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import tkinter, PIL" >nul 2>nul
    if %errorlevel%==0 (
        start "" py -3 "%~dp0app.py"
        exit /b 0
    )
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import tkinter, PIL" >nul 2>nul
    if %errorlevel%==0 (
        start "" python "%~dp0app.py"
        exit /b 0
    )
)

echo Non trovo Python con Tkinter e Pillow.
echo.
echo Installa Python 3, poi esegui:
echo python -m pip install -r requirements.txt
echo.
pause
exit /b 1
