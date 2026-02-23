# MyWhoosh Tulosten Käsittelijä - Jatkoideat ja Kehitys

Tähän tiedostoon on koottu ideoita projektin jatkokehitykseen uusia ominaisuuksia ja parannuksia varten.

## 1. Suorituskykydatan (W/kg) tuominen tulosgrafiikkaan
Vaikka luonnostelimme W/kg-sarakkeen poistamisen lopullisesta kuvasta tilan tai luettavuuden vuoksi, taustajärjestelmä ja tiedonhaku pystyy parsimaan sen onnistuneesti API:sta (kenttä: `wattPerKG`).
* **Mahdollinen toteutus:** Tehdään grafiikoiden luontiskriptiin (`luo_grafiikat.py`) asetus tai komentorivivipu (esim. `--show-wkg`), joka ottaa kyseisen sarakkeen dynaamisesti käyttöön niitä kilpailuja/yhteisöjä varten, jotka haluavat vertailla teholukemia pelkkien aikojen lisäksi.

## 2. Reittiprofiilin ja tietojen eristäminen AI:lla (Multimodaalisuus)
Tavoitteena on hyödyntää tekoälyn (esim. Gemini 3.1) multimodaalista näkökykyä kilpailun virallisen "reittikortin" (esim. profiilikuva) analysoinnissa ilman tarvetta monimutkaisille OCR- tai OpenCV-skripteille.
* **Tiedon poiminta chatin kautta:** Käyttäjä lataa reittikortin chattiin ennen tulosputken ajoa. Tekoäly lukee kuvasta automaattisesti perustiedot: matka (esim. 53.9 km), nousumetrit (esim. 932 m), päivämäärä ja reitin nimi.
* **Rataprofiilin luominen:** Tekoäly prosessoi ja piirtää kuvassa näkyvän reittiprofiilin tyylitellyksi, läpinäkyväksi PNG-silhuetiksi ja tallentaa sen nimellä `assets/current_route_profile.png`.
* **Integraatio tuloskuvaan:** Tulosputkea ajettaessa `luo_grafiikat.py` hakee tämän silhuetin ja tekstitiedot automaattisesti, lisäten reitin profiilin ja datan osaksi generoitaavaa lopullista tulosgrafiikkaa (esim. otsikon tai reunuksen yhteyteen).
