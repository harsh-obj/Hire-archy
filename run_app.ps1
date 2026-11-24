# =====================================================================
# HIRE-ARCHY 2.0: PYTHON DJANGO + REACT ATS SUITE (PowerShell Launcher)
# =====================================================================

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          HIRE-ARCHY 2.0: PYTHON DJANGO + REACT ATS SUITE           " -ForegroundColor Blue
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

Write-Host "[1/3] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVer = python --version
    Write-Host "       Found $pythonVer" -ForegroundColor Green
} catch {
    Write-Host " [ERROR] Python not found on PATH! Please install Python 3.10+." -ForegroundColor Red
    Pause
    Exit
}

Write-Host "[2/3] Checking dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet --no-warn-script-location
Write-Host "       Dependencies verified!" -ForegroundColor Green

Write-Host "[3/3] Launching Django Server (open to local network)..." -ForegroundColor Yellow
Write-Host "       Press Ctrl+C to stop the application." -ForegroundColor Cyan
Write-Host ""

python manage.py runserver 0.0.0.0:8000
