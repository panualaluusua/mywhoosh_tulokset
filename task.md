# Tehtävälista: Uusien Datalähteiden Tutkiminen

- [ ] Luo `inspect_api.py` kaikkien verkkopyyntöjen kaappaamiseksi
- [ ] Aja `inspect_api.py` ja tallenna vastaukset
- [x] Testaa uusi workflow

# Tehtävälista: Dynaaminen Palkintolaskenta

- [x] Päivitä `src/hae_tulokset.py` kaappaamaan tapahtuman tiedot (`event_details.json`)
- [x] Päivitä `src/palkintolaskuri.py` lukemaan palkintotiedot JSONista
    - [x] Toteuta valuuttamuunnos (AED -> USD)
    - [ ] Korvaa kovakoodatut taulukot dynaamisella datalla
- [ ] Testaa oikeellisuus (`test_dynamic_prizes.py`)lennetut JSON-tiedostot "prize" tai "money" -kenttien varalta
- [ ] Päivitä `hae_tulokset.py` käyttämään uutta lähdettä tarvittaessa
