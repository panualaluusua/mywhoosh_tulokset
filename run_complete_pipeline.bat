@echo off
if not exist ".venv\Scripts\python.exe" (
    echo Virtuaaliymparisto puuttuu. Ajetaan setup_env.bat...
    call setup_env.bat
)

echo ==========================================
echo MyWhoosh Palkintolaskenta - Koko Putki
echo ==========================================

:: Kysy URL
set /p target_url="Anna kisan URL (Jata tyhjaksi jos haluat kayttaa oletusta/koodattua): "
echo.
echo Valittu URL: %target_url%
echo.

:: Kysy Nimi ja Pvm (User request)
set /p race_name="Anna kisan nimi (Jata tyhjaksi jos haluat automaation): "
set /p race_date="Anna kisan pvm (Jata tyhjaksi jos haluat automaation): "
echo.

echo [1/6] Haetaan tiimitulokset (capture_team_data.py)...

:: SIIVOUS
echo     -> Poistetaan vanhat datatiedostot...
if exist output\*.json del output\*.json
if exist output\*.txt del output\*.txt

if "%target_url%"=="" (
    .venv\Scripts\python.exe src/capture_team_data.py
) else (
    .venv\Scripts\python.exe src/capture_team_data.py %target_url%
)
if %ERRORLEVEL% NEQ 0 goto error

echo [2/6] Haetaan yksilotulokset (hae_tulokset.py)...
if "%target_url%"=="" (
    .venv\Scripts\python.exe src/hae_tulokset.py
) else (
    .venv\Scripts\python.exe src/hae_tulokset.py %target_url%
)
if %ERRORLEVEL% NEQ 0 goto error

echo [3/6] Yhdistetaan tiimipalkinnot (merge_team_prizes.py)...
.venv\Scripts\python.exe src/merge_team_prizes.py
if %ERRORLEVEL% NEQ 0 goto error

echo [4/6] Lasketaan lopulliset palkinnot (palkintolaskuri.py)...
:: Argumentit: source_json, output_json, race_name, race_date, (event_id)
if "%race_name%"=="" (
    .venv\Scripts\python.exe src/palkintolaskuri.py tallenna_palkintodata
) else (
    .venv\Scripts\python.exe src/palkintolaskuri.py tallenna_palkintodata output/all_results.json output/palkintodata.json "%race_name%" "%race_date%"
)
if %ERRORLEVEL% NEQ 0 goto error

echo [5/6] Paivitetaan varastoa...
.venv\Scripts\python.exe src/paivita_varasto.py --file output/palkintodata.json

echo [6/6] Luodaan grafiikat...
if "%race_name%"=="" (
    .venv\Scripts\python.exe src/luo_grafiikat.py
) else (
    .venv\Scripts\python.exe src/luo_grafiikat.py output/all_results.json "%race_name%" "%race_date%"
)
if %ERRORLEVEL% NEQ 0 goto error

echo VALMIS!
pause
goto :EOF

:error
echo VIRHE! Tarkista ylla olevat ilmoitukset.
pause
