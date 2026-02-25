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

:: Kysy sukupuolikategoria (men/women)
set /p kisarata_gender="Anna sukupuolikategoria (men/women, Enter=men): "
if "%kisarata_gender%"=="" set kisarata_gender=men
echo Kategoria: %kisarata_gender%
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
.venv\Scripts\python.exe src/palkintolaskuri.py tallenna_palkintodata
if %ERRORLEVEL% NEQ 0 goto error

echo [5/7] Paivitetaan varastoa...
.venv\Scripts\python.exe src/paivita_varasto.py --file output/palkintodata.json

echo [6/7] Prosessoidaan ratasilhuetit (extract_silhouette.py)...
.venv\Scripts\python.exe src/extract_silhouette.py kisarata
if %ERRORLEVEL% NEQ 0 (
    echo Varoitus: Silhuettien prosessointi epaonnistui, jatketaan ilmankin.
)

echo [7/7] Luodaan grafiikat...
.venv\Scripts\python.exe src/luo_grafiikat.py output/all_results.json %kisarata_gender%
if %ERRORLEVEL% NEQ 0 goto error

echo VALMIS!
pause
goto :EOF

:error
echo VIRHE! Tarkista ylla olevat ilmoitukset.
pause
