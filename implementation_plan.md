# Toteutussuunnitelma: Palkintoraha-varaston Eriyttäminen

Tavoitteena on eriyttää palkintorahojen tallennus omaksi itsenäiseksi prosessikseen, jotta `hae_tulokset.py` pysyy puhtaana visualisointityökaluna.

## Muutokset

### 1. Uusi skripti: `src/paivita_varasto.py`
Luodaan uusi komentorivityökalu, joka vastaa tietovaraston päivityksestä.
*   **Syötteet:**
    *   `--file`: Lähdetiedosto (oletus: `palkintodata.json`)
    *   `--date`: Kisan pvm (oletus: kysytään / tänään)
    *   `--name`: Kisan nimi (oletus: kysytään)
*   **Toiminta:**
    1.  Lukee `palkintodata.json` (jonka `hae_tulokset.py` on luonut).
    2.  Kysyy puuttuvat tiedot käyttäjältä.
    3.  Kutsuu `tietovarasto.tallenna_kisa_csv`.

### 2. Muokkaus: `src/hae_tulokset.py`
*   Poistetaan `import tietovarasto` ja kutsu `tietovarasto.tallenna_kisa_csv`.
*   Säilytetään `tallenna_palkintodata` -kutsu, koska se tuottaa `palkintodata.json` -tiedoston, jota uusi skripti käyttää.

### 3. Työnkulku (Workflow)
1.  Käyttäjä ajaa `run.bat` (tai `hae_tulokset.py`) -> Syntyy tuloskuvat ja `palkintodata.json`.
2.  Käyttäjä ajaa `python src/paivita_varasto.py` (tai uusi bat) -> Palkinnot tallentuvat CSV:hen.

## Tiedostot
*   `[NEW] src/paivita_varasto.py`
*   `[MODIFY] src/hae_tulokset.py`
