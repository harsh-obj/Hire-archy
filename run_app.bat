@echo off
title Hire-archy ATS Resume Screener (Django)
echo =====================================================================
echo           HIRE-ARCHY 2.0: PYTHON DJANGO + REACT ATS SUITE
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ from python.org or Microsoft Store.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
pip install -r requirements.txt --quiet --no-warn-script-location

echo [3/3] Launching Django Development Server on http://127.0.0.1:8000...
echo.
echo Press CTRL+C in this window to stop the server.
echo.
start "" http://127.0.0.1:8000
python manage.py runserver 127.0.0.1:8000

pause
