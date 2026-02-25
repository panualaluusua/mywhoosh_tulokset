import csv
import os
import datetime
import sys

# Lisää src polkuun jotta importit toimivat
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from palkintolaskuri import get_all_prizes

OPT_IN_FILE = "opt_in_kuskit.txt"
CSV_FILE = "palkintokirjanpito.csv"
JSON_FILE = "all_results.json"

def load_opt_in_list():
    if not os.path.exists(OPT_IN_FILE):
        return []
    with open(OPT_IN_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Siisti rivit ja poista kommentit
    names = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return names

def save_prizes():
    print("--- Palkintojen Tallennus ---")
    
    # 1. Kysy tiedot
    # Try to load from kisarata data if available
    race_name = ""
    race_date = ""
    kisarata_file = r"C:\Users\panua\projektit\rataprofiili\kisarata\kisarata_men.json"
    if os.path.exists(kisarata_file):
        try:
            import json
            with open(kisarata_file, 'r', encoding='utf-8') as f:
                k_data = json.load(f)
                rd = k_data.get("race_details", {})
                race_name = rd.get("name", "")
                race_date = rd.get("date", "")
        except:
            pass

    if not race_name:
        race_name = "Syötetty Kisa" # Default if not found
    if not race_date:
        race_date = datetime.date.today().strftime("%Y-%m-%d")
        print(f"Käytetään tätä päivää: {race_date}")

    # Use arguments if we want to run headlessly, assume False for final if not specified
    is_final_input = os.environ.get("IS_FINAL", "e")
    is_final = is_final_input.lower() == 'k'

    # 2. Laske palkinnot
    print("Lasketaan palkintoja...")
    if not os.path.exists(JSON_FILE):
        print(f"Virhe: {JSON_FILE} puuttuu!")
        return

    try:
        print("Kutsutaan get_all_prizes...")
        prize_map, _ = get_all_prizes(JSON_FILE, is_final)
        print("get_all_prizes valmistui.")
    except Exception as e:
        print(f"VIRHE get_all_prizes kutsussa: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # DEBUG
    print(f"DEBUG: Prize Map Keys: {list(prize_map.keys())}")
    print(f"DEBUG: Teppo Prize: {prize_map.get('Teppo Testikuski')}")

    # 3. Lataa opt-in lista
    opt_in_names = load_opt_in_list()
    print(f"DEBUG: Opt-In Names: {opt_in_names}")
    if not opt_in_names:
        print(f"Varoitus: {OPT_IN_FILE} on tyhjä tai puuttuu. Kukaan ei ole antanut lupaa tallennukseen.")
        return

    # 4. Suodata ja tallenna
    new_rows = []
    print(f"\nTallennetaan seuraavat palkinnot ({len(opt_in_names)} seurattavaa kuskia):")
    
    for name in opt_in_names:
        prize = prize_map.get(name, 0)
        if prize > 0:
            print(f"  - {name}: ${int(prize)}")
            new_rows.append([race_date, race_name, name, int(prize)])
        else:
            # Voidaan tallentaa myös 0, jos halutaan seurata osallistumista
            # Käyttäjä halusi "tasmätä tilitetyn rahamäärän", joten 0 ei ehkä ole tarpeen, 
            # mutta se on hyvä tieto että on ajanut mutta ei voittanut.
            # Tallennetaan vain jos > 0 selkeyden vuoksi? 
            # Tai kysytään? Oletus: Vain voitot kiinnostavat kirjanpidossa.
            pass

    if not new_rows:
        print("Ei tallennettavaa (kukaan seurattavista ei voittanut rahaa tällä kertaa).")
        return

    # 5. Kirjoita CSV
    file_exists = os.path.exists(CSV_FILE)
    
    try:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Pvm", "Kisa", "Nimi", "Summa ($)"])
            
            writer.writerows(new_rows)
            
        print(f"\nOnnistui! Tiedot lisätty tiedostoon {CSV_FILE}")
    except Exception as e:
        print(f"Virhe tallennuksessa: {e}")

if __name__ == "__main__":
    save_prizes()
