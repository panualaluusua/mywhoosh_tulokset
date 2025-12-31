@echo off
python src/hae_tulokset.py

echo.
set /p save_prizes="Haluatko tallentaa palkintorahat tietovarastoon? (k/E): "
if /i "%save_prizes%"=="k" (
    python src/paivita_varasto.py
) else (
    echo Palkintoja ei tallennettu.
)

pause
