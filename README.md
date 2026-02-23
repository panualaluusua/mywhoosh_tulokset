# MyWhoosh Tulospalvelu

Työkalu MyWhoosh-kisatulosten hakemiseen, palkintojen laskemiseen ja grafiikoiden luomiseen.

## Asennus

1.  Asenna Python (3.8+).
2.  Asenna riippuvuudet:
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

## Dokumentaatio

Tarkemmat ohjeet löytyvät `docs/` -kansiosta:
- [Käyttöohje](docs/KAYTTOOHJE.md)
- [Tekninen dokumentaatio](docs/TEKNINEN_DOKUMENTAATIO.md)

## Käyttö

Aja koko putki **`run_complete_pipeline.bat`** -tiedostolla:
```bash
run_complete_pipeline.bat
```
Tämä komentosarja:
1.  Hakee tulokset MyWhooshista (kysyy URL/ID jos ei annettu).
2.  Laskee palkinnot (ml. Sprint/KOM ja tiimipisteet).
3.  Luo tulosgrafiikat `kuvat/` -kansioon.
4.  Luo raportit `tulokset.txt` ja `palkintodata.json`.
5.  (Valinnainen) Tallentaa palkinnot tietovarastoon (`data/palkintohistoria.csv`).

## Rakenne

*   `src/`: Python-lähdekoodit.
    *   `hae_tulokset.py`: Datan haku APIsta.
    *   `palkintolaskuri.py`: Palkintojen laskenta.
    *   `luo_grafiikat.py`: Kuvien generointi.
    *   `paivita_varasto.py`: Tietokannan päivitys.
*   `assets/`: Ikonit ja muut resurssit.
*   `kuvat/`: Generoidut tuloskuvat.
*   `data/palkintohistoria.csv`: Tietokanta palkinnoista.
