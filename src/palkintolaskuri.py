import pandas as pd
import json
import os

# Palkintotaulukot (Dynaaminen lataus)
PRIZES_INDIVIDUAL = {}
PRIZES_TEAM = {}
PRIZES_SPRINT = {}
PRIZES_KOM = {}
PRIZES_SEGMENT = {}

def load_dynamic_prizes(event_details_file="event_details.json"):
    """
    Lataa palkintotiedot event_details.json -tiedostosta.
    Muuntaa AED -> USD (tai käyttää conversionRatea).
    """
    global PRIZES_INDIVIDUAL, PRIZES_TEAM, PRIZES_SPRINT, PRIZES_KOM, PRIZES_SEGMENT
    
    if not os.path.exists(event_details_file):
        print(f"Varoitus: {event_details_file} puuttuu. Käytetään tyhjiä palkintotaulukoita.")
        return

    try:
        with open(event_details_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        prize_data = data.get('data', {}).get('prizeMoney', {})
        if not prize_data:
            print("Varoitus: Palkintodataa ei löytynyt JSONista.")
            return

        rate = prize_data.get('conversionRate', 1.0)
        categories = prize_data.get('categories', {})
        
        print(f"Ladataan palkintoja. Valuuttakurssi: {rate}")
        
        PRIZES_INDIVIDUAL = {}
        PRIZES_TEAM = {}
        PRIZES_SPRINT = {}
        PRIZES_KOM = {}
        
        for cat_id_str, cat_data in categories.items():
            cat_id = int(cat_id_str)
            
            # Individual
            indiv_raw = cat_data.get('individual', {}).get('prizes', [])
            PRIZES_INDIVIDUAL[cat_id] = [round(p / rate) for p in indiv_raw]
            
            # Team
            team_raw = cat_data.get('teams', {}).get('prizes', [])
            PRIZES_TEAM[cat_id] = [round(p / rate) for p in team_raw]

            # Sprint (gateType 9)
            sprint_raw = cat_data.get('9', {}).get('prizes', [])
            PRIZES_SPRINT[cat_id] = [round(p / rate) for p in sprint_raw]

            # KOM (gateType 4)
            kom_raw = cat_data.get('4', {}).get('prizes', [])
            PRIZES_KOM[cat_id] = [round(p / rate) for p in kom_raw]

            # Segment Winners (gateType 'segments')
            seg_raw = cat_data.get('segments', {}).get('prizes', [])
            PRIZES_SEGMENT[cat_id] = [round(p / rate) for p in seg_raw]
            
        print("Palkintotaulukot päivitetty dynaamisesti (Indiv, Team, Sprint, KOM, Segments).")
        
    except Exception as e:
        print(f"Virhe palkintojen latauksessa: {e}")

# Alusta tyhjät, täytetään myöhemmin
PRIZES_INDIVIDUAL = {}
PRIZES_TEAM = {}

def get_all_prizes(json_file="all_results.json", is_final=False):
    """
    Laskee kaikille ajajille kokonaispalkinnon (Henkilökohtainen + Tiimiosuus).
    Jos is_final on False, lasketaan vain henkilökohtaiset.
    
    HUOM: Tiimisijoitukset lasketaan KOKO datasta (kaikki maat), 
    mutta palautetaan vain suomalaisten palkinnot ja sijoitukset.
    
    Palauttaa:
      prize_map: { "Ajajan Nimi": palkinto_summa } (Vain Suomalaiset)
      team_rank_map: { "Ajajan Nimi": tiimisijoitus (int) } (Vain Suomalaiset)
    """
    if not os.path.exists(json_file):
        return {}, {}

    # Lataa dynaamiset palkinnot
    load_dynamic_prizes()

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- 1. LASKETAAN TIIMISIJOITUKSET (KOKO DATA) ---
    team_rank_by_name = {}   # { "Clean Team Name": rank }
    team_prize_share = {}    # { "Clean Team Name": share_per_member }
    
    if is_final:
        df_all = pd.DataFrame(data)
        
        # Varmista sarakkeet
        required_cols = ['categoryId', 'teamName', 'finishedTime', 'selectionStatus', 'userFullName']
        for col in required_cols:
            if col not in df_all.columns:
                df_all[col] = None

        # Siivotaan tiiminimet
        df_all['clean_team_name'] = df_all['teamName'].fillna("").astype(str).str.strip()

        # Ryhmittele kategorialla
        for cat_id, cat_group in df_all.groupby('categoryId'):
            if cat_id not in PRIZES_TEAM:
                continue
            
            team_results = []
            
            # Ryhmittele SIIVOTUN tiiminimen mukaan
            for team_name, team_group in cat_group.groupby('clean_team_name'):
                # Ohita tyhjät ja yksilöt
                if team_name in ["", "-", "Individual", "None", "nan"]: 
                    continue
                    
                # Ota vain ne joilla on hyväksytty aika (ei DNF/0) JA ei ole diskattu (ANL)
                valid_times = team_group[
                    (team_group['finishedTime'] > 0) & 
                    (team_group['selectionStatus'] != "ANL")
                ].copy()
                
                valid_times = valid_times.sort_values('finishedTime')
                
                # Tarvitaan vähintään 3 ajajaa tuloksen saamiseksi
                if len(valid_times) >= 3:
                    top3 = valid_times.head(3)
                    total_time = top3['finishedTime'].sum()
                    
                    team_results.append({
                        'team': team_name, 
                        'total_time_ms': total_time,
                        'total_members': len(team_group) # Kaikki jäsenet palkinnon jakoa varten
                    })
            
            # Järjestä tiimit ajan mukaan
            team_results.sort(key=lambda x: x['total_time_ms'])
            
            # Jaa palkinnot ja tallenna sijoitukset
            prizes = PRIZES_TEAM[cat_id]
            
            for i, res in enumerate(team_results):
                rank = i + 1
                t_name = res['team']
                team_rank_by_name[t_name] = rank
                
                if rank <= len(prizes):
                    total_prize = prizes[rank-1]
                    # Jaa palkinto KAIKKIEN jäsenten kesken
                    num_members = res['total_members']
                    if num_members > 0:
                        share = total_prize / num_members
                        team_prize_share[t_name] = share

    # --- 2. LASKETAAN HENKILÖKOHTAISET & YHDISTETÄÄN (VAIN SUOMALAISET) ---
    finnish_riders = [r for r in data if r.get('userCountryFlag') == 82]
    
    if not finnish_riders:
        return {}, {}

    df_fin = pd.DataFrame(finnish_riders)
    # Varmista sarakkeet myös tässä
    for col in ['categoryId', 'calculated_rank', 'userFullName', 'teamName', 'selectionStatus']:
        if col not in df_fin.columns:
            df_fin[col] = None
            
    df_fin['clean_team_name'] = df_fin['teamName'].fillna("").astype(str).str.strip()

    prize_map = {}
    team_rank_map = {} # Palautetaan: { "Ajajan Nimi": rank }

    for index, row in df_fin.iterrows():
        name = row['userFullName']
        cat = row['categoryId']
        rank = row['calculated_rank']
        status = row.get('selectionStatus', '')
        t_name_clean = row['clean_team_name']
        
        # Alusta
        if name not in prize_map:
            prize_map[name] = 0
            
        # A. Henkilökohtainen palkinto
        if status != "ANL":
            if cat in PRIZES_INDIVIDUAL:
                prizes = PRIZES_INDIVIDUAL[cat]
                if 1 <= rank <= len(prizes):
                    prize_map[name] += prizes[rank-1]

        # B. Tiimipalkinto & Sijoitus
        # ... (rest is same) ...
        # Hae sijoitus (vaikka olisi ANL, sijoitus on olemassa jos tiimi pärjäsi)
        if t_name_clean in team_rank_by_name:
            team_rank_map[name] = team_rank_by_name[t_name_clean]
            
            # Lisää palkinto-osuus JOS ei ANL
            if status != "ANL" and t_name_clean in team_prize_share:
                prize_map[name] += team_prize_share[t_name_clean]

    return prize_map, team_rank_map

def laske_palkinto_erittely(json_file="all_results.json"):
    """
    Laskee palkinnot eritellen henkilökohtaisen ja tiimiosuuden.
    Palauttaa listan sanakirjoja:
    [
      {
        "nimi": "Matti",
        "tiimi": "Team",
        "kategoria": 1,
        "individual": 100,
        "team_share": 50,
        "total": 150
      },
      ...
    ]
    """
    if not os.path.exists(json_file):
        return []

    # Lataa dynaamiset palkinnot
    load_dynamic_prizes()

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- 1. LASKETAAN TIIMIPOTIT (KOKO DATA) ---
    team_prize_share = {}    # { "Clean Team Name": share_per_member }
    team_ranks = {}          # { "Clean Team Name": rank }
    
    df_all = pd.DataFrame(data)
    required_cols = ['categoryId', 'teamName', 'finishedTime', 'selectionStatus', 'userFullName']
    for col in required_cols:
        if col not in df_all.columns:
            df_all[col] = None
    df_all['clean_team_name'] = df_all['teamName'].fillna("").astype(str).str.strip()

    for cat_id, cat_group in df_all.groupby('categoryId'):
        if cat_id not in PRIZES_TEAM:
            continue
        
        team_results = []
        for team_name, team_group in cat_group.groupby('clean_team_name'):
            if team_name in ["", "-", "Individual", "None", "nan"]: 
                continue
            valid_times = team_group[
                (team_group['finishedTime'] > 0) & 
                (team_group['selectionStatus'] != "ANL")
            ].copy()
            valid_times = valid_times.sort_values('finishedTime')
            
            if len(valid_times) >= 3:
                top3 = valid_times.head(3)
                total_time = top3['finishedTime'].sum()
                team_results.append({
                    'team': team_name, 
                    'total_time_ms': total_time,
                    'total_members': len(team_group)
                })
        
        team_results.sort(key=lambda x: x['total_time_ms'])
        prizes = PRIZES_TEAM[cat_id]
        
        for i, res in enumerate(team_results):
            rank = i + 1
            team_ranks[res['team']] = rank
            
            if rank <= len(prizes):
                total_prize = prizes[rank-1]
                if res['total_members'] > 0:
                    share = round(total_prize / res['total_members'], 2)
                    team_prize_share[res['team']] = share

    # --- 1.5 LASKETAAN SPRINT & KOM PALKINNOT ---
    # { userId: {'amount': 0, 'types': []} }
    extra_prizes_data = {} 
    
    def add_extra_prize(uid, amount, prize_type):
        if uid not in extra_prizes_data:
            extra_prizes_data[uid] = {'amount': 0, 'types': []}
        extra_prizes_data[uid]['amount'] += amount
        extra_prizes_data[uid]['types'].append(prize_type)

    # Create a set of valid user IDs (finishers) from the main data
    valid_user_ids = set(r.get('userId') for r in data if r.get('result_status') != 'DNF') 
    
    def process_segment_file(filename, overall_prize_table, segment_prize_table, type_overall, type_segment):
        if not os.path.exists(filename):
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                seg_data = json.load(f)
            
            if "data" in seg_data and "resultData" in seg_data["data"]:
                results = seg_data["data"]["resultData"]
                
                # Group by Category
                by_cat = {}
                for r in results:
                    c = r.get('categoryId')
                    if c not in by_cat: by_cat[c] = []
                    by_cat[c].append(r)
                    
                for cat_id, cat_results in by_cat.items():
                    # 1. OVERALL (Points based)
                    if cat_id in overall_prize_table:
                        # Sum points per user
                        user_points = {}
                        for r in cat_results:
                            uid = r.get('userId')
                            # Filter by valid finishers
                            if uid not in valid_user_ids:
                                continue
                                
                            pts = r.get('points', 0)
                            if uid:
                                user_points[uid] = user_points.get(uid, 0) + pts
                        
                        # Sort by points (desc)
                        sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
                        
                        prizes = overall_prize_table[cat_id]
                        for i, (uid, pts) in enumerate(sorted_users):
                            rank = i + 1
                            if rank <= len(prizes):
                                amount = prizes[rank-1]
                                add_extra_prize(uid, amount, type_overall)

                    # 2. SEGMENT WINNERS (Time based per gate)
                    if cat_id in segment_prize_table:
                        # Group by gateId
                        by_gate = {}
                        for r in cat_results:
                            gid = r.get('gateId')
                            if gid not in by_gate: by_gate[gid] = []
                            by_gate[gid].append(r)
                            
                        seg_prizes = segment_prize_table[cat_id]
                        
                        for gid, gate_results in by_gate.items():
                            # Filter valid times and sort by finishedTimeOverall (asc) -> First Across Line
                            # AND filter by valid finishers
                            valid = [r for r in gate_results if r.get('finishedTimeOverall', 0) > 0 and r.get('userId') in valid_user_ids]
                            valid.sort(key=lambda x: x.get('finishedTimeOverall', 9999999999))
                            
                            for i, r in enumerate(valid):
                                rank = i + 1
                                if rank <= len(seg_prizes):
                                    amount = seg_prizes[rank-1]
                                    uid = r.get('userId')
                                    if uid:
                                        add_extra_prize(uid, amount, type_segment)

        except Exception as e:
            print(f"Virhe segmenttitiedoston {filename} käsittelyssä: {e}")

    # process_segment_file("sprint_results.json", PRIZES_SPRINT, PRIZES_SEGMENT, "sprint_overall", "sprint_segment")
    # process_segment_file("kom_results.json", PRIZES_KOM, PRIZES_SEGMENT, "kom_overall", "kom_segment")

    # --- 2. LASKETAAN HENKILÖKOHTAISET (VAIN SUOMALAISET) ---
    finnish_riders = [r for r in data if r.get('userCountryFlag') == 82]
    results_list = []

    for rider in finnish_riders:
        name = rider.get('userFullName', 'Unknown')
        cat = rider.get('categoryId', 0)
        rank = rider.get('calculated_rank', 999)
        status = rider.get('selectionStatus', '')
        t_name = rider.get('teamName', '')
        t_name_clean = str(t_name).strip() if t_name else ""
        
        indiv_prize = 0
        team_share = 0
        t_rank = team_ranks.get(t_name_clean, '-')
        
        if status != "ANL":
            # Indiv
            if cat in PRIZES_INDIVIDUAL:
                p_list = PRIZES_INDIVIDUAL[cat]
                if 1 <= rank <= len(p_list):
                    indiv_prize = p_list[rank-1]
            
            # Team
            if t_name_clean in team_prize_share:
                team_share = team_prize_share[t_name_clean]
        
        # Extra prizes (Sprint/KOM)
        uid = rider.get('userId')
        extra_data = extra_prizes_data.get(uid, {'amount': 0, 'types': []})
        extra = extra_data['amount']
        achievements = list(set(extra_data['types'])) # Deduplicate
        
        if indiv_prize > 0 or team_share > 0 or extra > 0:
            results_list.append({
                "nimi": name,
                "tiimi": t_name,
                "kategoria": cat,
                "sijoitus": rank,
                "tiimisijoitus": t_rank,
                "individual": indiv_prize,
                "team_share": team_share,
                "extra": extra,
                "total": indiv_prize + team_share + extra,
                "achievements": achievements
            })
            
    return results_list

def tallenna_palkintodata(json_file="all_results.json", output_file="palkintodata.json", race_name="", race_date="", event_id=""):
    """
    Laskee palkinnot ja tallentaa ne JSON-tiedostoon myöhempää käyttöä varten.
    Tallentaa myös kisan metatiedot.
    """
    prizes = laske_palkinto_erittely(json_file)
    
    data = {
        "meta": {
            "race_name": race_name,
            "race_date": race_date,
            "event_id": event_id
        },
        "prizes": prizes
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Palkintodata tallennettu: {output_file}")
    return data

def save_results_report(json_file="all_results.json", output_file="tulokset.txt"):
    """
    Luo tekstitiedoston, jossa on jokaisen suomalaisen ajajan:
    - Nimi
    - Kategoria
    - Henkilökohtainen sijoitus
    - Tiimi
    - Tiimisijoitus
    """
    if not os.path.exists(json_file):
        print(f"Virhe: Tiedostoa {json_file} ei löydy.")
        return

    # 1. Hae palkintotiedot ja tiimisijoitukset
    # Käytetään is_final=True, jotta tiimisijoitukset lasketaan
    prize_map, team_rank_map = get_all_prizes(json_file, is_final=True)

    # 2. Lataa data uudelleen raportointia varten
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Suodata suomalaiset
    finnish_riders = [r for r in data if r.get('userCountryFlag') == 82]
    
    # Järjestä kategorialla ja sijoituksella
    finnish_riders.sort(key=lambda x: (x.get('categoryId', 999), x.get('calculated_rank', 999)))

    print(f"Kirjoitetaan tulokset tiedostoon: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"{'Nimi':<30} | {'Kat':<5} | {'Sij':<5} | {'Tiimi':<30} | {'Tiimisij':<10} | {'Status':<10}\n")
        f.write("-" * 100 + "\n")

        for rider in finnish_riders:
            name = str(rider.get('userFullName', 'Unknown') or 'Unknown')
            cat = str(rider.get('categoryId', '-') or '-')
            rank = str(rider.get('calculated_rank', '-') or '-')
            team = str(rider.get('teamName', '-') or '-')
            status = str(rider.get('selectionStatus', '') or '')
            
            # Hae tiimisijoitus lasketusta mapista
            team_rank = str(team_rank_map.get(name, '-') or '-')

            f.write(f"{name:<30} | {cat:<5} | {rank:<5} | {team:<30} | {team_rank:<10} | {status:<10}\n")

    print("Valmis.")

if __name__ == "__main__":
    # Kun ajetaan suoraan, luo raportti
    save_results_report()
