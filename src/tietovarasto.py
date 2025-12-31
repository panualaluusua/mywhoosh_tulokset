import csv
import os
import palkintolaskuri

CSV_FILE = "palkintohistoria.csv"
OPT_IN_FILE = "seurattavat.txt"

def lue_seurattavat():
    """Lukee seurattavat.txt tiedoston ja palauttaa nimitietokannan (set)."""
    if not os.path.exists(OPT_IN_FILE):
        return set()
    
    with open(OPT_IN_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return set()
        # Oletetaan erottimeksi puolipiste
        names = [n.strip() for n in content.split(';') if n.strip()]
        return set(names)

def tallenna_kisa_csv(race_date=None, race_name=None, palkinto_json="palkintodata.json", event_id="Unknown"):
    """
    Tallentaa kisan palkintotiedot CSV-tiedostoon.
    Lukee valmiiksi lasketun palkintodatan (palkintodata.json).
    Vain seurattavat.txt -listalla olevat tallennetaan.
    """
    # 1. Hae seurattavat
    allowed_names = lue_seurattavat()
    if not allowed_names:
        print(f"Ei seurattavia ajajia ({OPT_IN_FILE} on tyhjä tai puuttuu). Palkintoja ei tallennettu.")
        return

    # 2. Lue valmis palkintodata
    if not os.path.exists(palkinto_json):
        print(f"Virhe: {palkinto_json} puuttuu.")
        return

    try:
        import json
        with open(palkinto_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Handle new structure with metadata
        if isinstance(data, dict) and "meta" in data:
            meta = data["meta"]
            prizes = data["prizes"]
            
            # Use metadata if args are missing
            if not race_date: race_date = meta.get("race_date")
            if not race_name: race_name = meta.get("race_name")
            if not event_id or event_id == "Unknown": event_id = meta.get("event_id")
        else:
            # Fallback for old list format
            prizes = data
            
    except Exception as e:
        print(f"Virhe luettaessa palkintodataa: {e}")
        return

    # 3. Suodata ja muotoile uudet rivit
    new_rows = []
    count = 0
    
    for p in prizes:
        name = p['nimi']
        if name in allowed_names:
            # Henkilökohtainen
            if p['individual'] > 0:
                new_rows.append({
                    'EventID': event_id,
                    'Pvm': race_date,
                    'Kisa': race_name,
                    'Ajaja': name,
                    'Tiimi': p['tiimi'],
                    'Kategoria': p['kategoria'],
                    'Sijoitus': p['sijoitus'],
                    'Tiimisijoitus': p['tiimisijoitus'],
                    'Summa': p['individual'],
                    'Tyyppi': 'individual',
                    'Status': 'odottaa'
                })
            
            # Tiimi
            if p['team_share'] > 0:
                new_rows.append({
                    'EventID': event_id,
                    'Pvm': race_date,
                    'Kisa': race_name,
                    'Ajaja': name,
                    'Tiimi': p['tiimi'],
                    'Kategoria': p['kategoria'],
                    'Sijoitus': p['sijoitus'],
                    'Tiimisijoitus': p['tiimisijoitus'],
                    'Summa': f"{p['team_share']:.2f}",
                    'Tyyppi': 'team',
                    'Status': 'odottaa'
                })
            count += 1

    if not new_rows:
        print("Ei tallennettavia palkintoja (kukaan seurattavista ei saanut palkintoa).")
        return

    # 4. Lue vanha CSV ja poista vanhat rivit tälle kisalle (EventID perusteella)
    fieldnames = ['EventID', 'Pvm', 'Kisa', 'Ajaja', 'Tiimi', 'Kategoria', 'Sijoitus', 'Tiimisijoitus', 'Summa', 'Tyyppi', 'Status']
    kept_rows = []
    
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                # Tarkista onko EventID sarake olemassa
                if 'EventID' not in reader.fieldnames:
                    print("Huom: Vanha CSV-formaatti havaittu. Lisätään EventID sarake.")
                    for row in reader:
                        row['EventID'] = 'Legacy'
                        if not (row['Pvm'] == race_date and row['Kisa'] == race_name):
                            kept_rows.append(row)
                else:
                    for row in reader:
                        if row['EventID'] != event_id:
                            kept_rows.append(row)
                            
        except Exception as e:
            print(f"Virhe luettaessa vanhaa CSV-tiedostoa: {e}")
            return

    # 5. Kirjoita kaikki takaisin
    try:
        with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(kept_rows)
            writer.writerows(new_rows)
            
        print(f"Tallennettu {len(new_rows)} palkintoriviä tiedostoon {CSV_FILE} (EventID: {event_id}).")
        
    except Exception as e:
        print(f"Virhe kirjoitettaessa CSV-tiedostoa: {e}")
