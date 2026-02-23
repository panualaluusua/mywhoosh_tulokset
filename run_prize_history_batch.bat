@echo off
echo ==========================================
echo MyWhoosh Palkintohistoria - Batch Process
echo ==========================================
echo.
echo Talla ajolla haetaan palkintotiedot useammasta kisasta kerralla.
echo Tulokset tallennetaan 'palkintohistoria.csv' tiedostoon.
echo.

:menu
echo Valitse syottotapa:
echo 1) Lue tiedostosta (data\input_urls.txt)
echo 2) Syota URLit manuaalisesti (kopioi-liita)
echo.
set /p choice="Valinta (1/2): "

if "%choice%"=="1" goto file_input
if "%choice%"=="2" goto manual_input
goto menu

:file_input
if not exist data\input_urls.txt (
    echo.
    echo VIRHE: data\input_urls.txt ei loydy!
    echo Luo tiedosto ja listaa URLit sinne.
    pause
    goto menu
)
python src/process_prize_history.py data/input_urls.txt
goto end

:manual_input
echo.
echo Syota URLit, yksi per rivi. Paina Enter kahdesti lopettaaksesi.
python src/process_prize_history.py
goto end

:end
echo.
echo Valmis! Tarkista palkintohistoria.csv.
pause
