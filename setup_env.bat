@echo off
echo ==========================================
echo MyWhoosh Palkintolaskenta - Ympariston Asennus
echo ==========================================

if not exist ".venv" (
    echo Luodaan virtuaaliymparisto .venv...
    python -m venv .venv
) else (
    echo Virtuaaliymparisto loytyy jo.
)

echo.
echo Asennetaan/paivitetaan riippuvuudet...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium

echo.
echo Valmis! Nyt voit ajaa run_complete_pipeline.bat
echo.
pause
