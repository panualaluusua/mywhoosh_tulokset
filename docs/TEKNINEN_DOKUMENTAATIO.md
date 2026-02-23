# Tekninen Dokumentaatio

## Arkkitehtuuri

Projekti koostuu sarjasta Python-skriptejä, joita ajetaan peräkkäin `run_complete_pipeline.bat` -batch-tiedoston ohjaamana.

### Tiedostot ja roolit

1. **`run_complete_pipeline.bat`**
   - Pääohjelma.
   - Hoitaa siivouksen (`del *.json`).
   - Kysyy käyttäjältä parametrit (URL, Nimi, Pvm).
   - Kutsuu Python-skriptejä järjestyksessä.

2. **`src/hae_tulokset.py`** (Playwright)
   - Hakee yksilötulokset (`getEventResults` API).
   - Skrollaa sivua ("Lazy loading") varmistaakseen että kaikki ajajat latautuvat.
   - Hakee sprint/KOM -datat.
   - Tallentaa metadatan (`full_event_details.json`).
   - Tuottaa: `all_results.json` (alustava).

3. **`capture_team_data.py`** (Playwright)
   - Navigoi tulossivun "Teams"-välilehdelle.
   - Interceptoi verkkoliikenteen ja tallentaa tiimien JSON-datat (`captured_team_data_*.json`).

4. **`merge_team_prizes.py`**
   - Lukee `all_results.json` ja `captured_team_data_*.json`.
   - Matching: Yhdistää tiimipalkinnot (`team_share`) yksilöihin `userId`:n perusteella.
   - **Injektio**: Jos tiimidatassa on ajaja, jota ei löydy `all_results.json`:sta (esim. API-latausvirheen takia), skripti luo hänelle uuden merkinnän tuloslistaan.
   - Päivittää `all_results.json`.

5. **`src/palkintolaskuri.py`**
   - Lukee `all_results.json`.
   - Suodattaa suomalaiset (`userCountryFlag == 82` tai URL-lippu "finland").
   - Laskee lopulliset palkinnot (Yksilö + Tiimi).
   - Tukee komentoriviargumentteja kisan nimen/pvm:n pakottamiseksi.
   - Tuottaa: `palkintodata.json`, `tulokset.txt`.

6. **`src/luo_grafiikat.py`**
   - Lukee `all_results.json` (tai `palkintodata.json`).
   - Renderöi PNG-kuvan (`PIL` kirjasto).
   - Käyttää dynaamista skaalausta (sovittaa fontit ja rivit kuvan korkeuteen).
   - Tuottaa: `kuvat/tulokset_kooste_*.png`.

## Tietovirrat

```mermaid
graph TD
    User[Käyttäjä] -->|URL, Nimi| Bat[run_complete_pipeline.bat]
    Bat -->|Siivous| Clean[Del *.json]
    Bat -->|URL| Hae[hae_tulokset.py]
    Hae -->|API| AllRes[all_results.json]
    Hae -->|Metadata| Meta[full_event_details.json]
    
    Bat -->|URL| Cap[capture_team_data.py]
    Cap -->|API| TeamData[captured_team_data_*.json]
    
    Bat --> Merge[merge_team_prizes.py]
    AllRes --> Merge
    TeamData --> Merge
    Merge -->|Injektio & Päivitys| AllResUpdated[all_results.json (Merged)]
    
    Bat -->|Nimi/Pvm| Laskuri[palkintolaskuri.py]
    AllResUpdated --> Laskuri
    Laskuri --> PalkData[palkintodata.json]
    
    Bat -->|Nimi/Pvm| Graf[luo_grafiikat.py]
    AllResUpdated --> Graf
    Graf --> Png[kuvat/kuva.png]
```

## Huomioitavaa

- **Injektio-logiikka**: Tämä on kriittinen ominaisuus. Koska MyWhoosh API lataa tuloksia "laiskoina" (lazy load), joskus `hae_tulokset.py` ei saa kaikkia rivejä. `merge_team_prizes.py` paikkaa tämän lisäämällä puuttuvat kuskit, jos he ovat saaneet tiimipalkinnon.
- **Riippuvuudet**: Python-kirjastot (`playwright`, `pandas`, `Pillow`). Playwright vaatii selaimen asennuksen (`playwright install`).
