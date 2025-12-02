# MyWhoosh Tuloshaku

Tämä ohjelma hakee MyWhoosh-kisojen tulokset, laskee sijoitukset ja suodattaa suomalaiset osallistujat.

## Asennus
Varmista että Python ja tarvittavat kirjastot on asennettu:
```bash
pip install -r requirements.txt
playwright install chromium
```

## Käyttö
Käynnistä ohjelma tuplaklikkaamalla `hae_tulokset.py` tai komentoriviltä:

```bash
python hae_tulokset.py
```

Ohjelma kysyy:
1.  **Tapahtuman URL tai Event ID**: (Pakollinen)
2.  **Kisan nimi**: (Valinnainen, esim. "MYWHOOSH SUNDAY RACE")
3.  **Kisan pvm**: (Valinnainen, esim. "1.12.2025")
4.  **Onko kyseessä Finaali?**: (k/E) Oletus on Ei (paina Enter). Jos vastaat Kyllä, tiimipalkinnot lasketaan mukaan.

Nämä tiedot tulostetaan kuviin alaotsikoksi.

## Tulokset
Ohjelma luo seuraavat tiedostot:
1.  **kuvat/**: Kansiollinen valmiita infograafikuvia. Tärkein on `tulokset_kooste_KISAN_NIMI_PVM.png` (tai `tulokset_kooste.png` jos tietoja ei annettu).
2.  **results.md**: Tekstimuotoinen taulukko suomalaisista.
3.  **all_results.json**: Kaikkien osallistujien raakadata JSON-muodossa.

## Tiedostot
- `hae_tulokset.py`: Pääohjelma (hakee datan ja kutsuu grafiikkamoottoria).
- `luo_grafiikat.py`: Grafiikkamoottori (piirtää kuvat).
- `tuloslistapohja.jpg`: Taustakuva grafiikoille.
- `Hae MyWhoosh Tulokset.bat`: Käynnistystiedosto.
