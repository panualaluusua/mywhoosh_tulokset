# MyWhoosh Palkintolaskuri - Käyttöohje

Tämä työkalu automatisoi MyWhoosh-kisojen tulosten haun (mukaan lukien tiimipalkinnot), palkintojen laskennan ja tulosgrafiikoiden luonnin.

## Pikaohje

1. Avaa komentokehote (tai klikkaa) **`run_complete_pipeline.bat`**.
2. Kun ohjelma kysyy **URL**, liitä kisan tulossivun osoite (esim. `https://results.mywhoosh.com/result/...`).
   - Jos haluat käyttää oletusta (Miesten kisa), paina vain Enter.
3. Ohjelma kysyy **Kisan nimeä** ja **Päivämäärää**.
   - Voit syöttää ne käsin (esim. "SRC - Women Finals", "25.1.2026").
   - Jos jätät tyhjäksi, ohjelma yrittää päätellä ne automaattisesti kisadatasta.
4. Odota, kunnes ohjelma on valmis.

## Mitä ohjelma tekee?

1. **Siivoaa projektin**: Poistaa vanhat tulostiedostot varmistaakseen puhtaan kisan.
2. **Hakee tulokset**: Käynnistää selaimen taustalla ja hakee tuloslistan (skrollaa alas, jotta kaikki ajajat latautuvat).
3. **Hakee tiimidatan**: Käy erikseen "Teams"-välilehdellä hakemassa tiimipalkinnot.
4. **Yhdistää datat**: Yhdistää henkilökohtaiset tulokset ja tiimipalkinnot. Jos joku ajaja puuttuu listalta (mutta on tiimissä), hänet lisätään ("injektoidaan") automaattisesti.
5. **Laskee palkinnot**: Laskee lopulliset tienestit (henkilökohtainen + tiimiosuus).
6. **Luo grafiikat**: Tallentaa tuloslistan kuvana kansioon `kuvat/`.
7. **Päivittää varaston**: Tallentaa palkinnot `data/palkintohistoria.csv` -tiedostoon (ei aktiivinen oletuksena kaikille, tarkista `paivita_varasto.py` asetukset).

## Tulokset

- **Graafinen tuloslista**: Löytyy kansiosta `kuvat/` (esim. `tulokset_kooste_SRC_Women_Finals_25_1_2026.png`).
- **Tekstiraportti**: `tulokset.txt`
- **Raakadata**: `all_results.json`, `palkintodata.json`.

## Vianmääritys

- **"Unknown Race"**: Jos automaattinen tunnistus ei löydä nimeä, aja ohjelma uudelleen ja syötä nimi käsin.
- **Puuttuvat ajajat**: Ohjelma yrittää korjata tämän automaattisesti (`merge_team_prizes.py`). Jos ongelmia ilmenee, varmista että URL on oikein.
