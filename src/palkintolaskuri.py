import pandas as pd
import json
import os

# Palkintotaulukot (Samat kuin aiemmin)
# Palkintotaulukot
PRIZES_INDIVIDUAL = {
    1: [2170, 1630, 1360, 820, 540, 490, 440, 330, 240, 140], # Category 1
    2: [1310, 980, 820, 490, 330, 290, 260, 200, 150, 80],    # Category 2
    3: [780, 590, 490, 290, 196, 180, 160, 120, 90, 50],      # Category 3
    4: [470, 350, 290, 180, 120, 110, 90, 80, 50, 30],        # Category 4
    5: [280, 200, 180, 100, 70, 65, 55, 40, 30, 20],          # Category 5
    6: [170, 130, 110, 60, 45, 40, 35, 30, 20, 10],           # Category 6
}

PRIZES_TEAM = {
    1: [9520, 6800, 5440, 3270, 2720, 2180, 1360], # Category 1 Teams
    2: [5710, 4080, 3270, 1960, 1630, 1310, 820],  # Category 2 Teams
    3: [3430, 2450, 1960, 1180, 980, 780, 490],    # Category 3 Teams
    4: [2000, 1470, 1200, 700, 590, 470, 295],     # Category 4 Teams
    5: [1230, 890, 710, 430, 350, 280, 180],       # Category 5 Teams
    6: [740, 530, 430, 250, 210, 170, 110],        # Category 6 Teams
}

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
        # Hae sijoitus (vaikka olisi ANL, sijoitus on olemassa jos tiimi pärjäsi)
        if t_name_clean in team_rank_by_name:
            team_rank_map[name] = team_rank_by_name[t_name_clean]
            
            # Lisää palkinto-osuus JOS ei ANL
            if status != "ANL" and t_name_clean in team_prize_share:
                prize_map[name] += team_prize_share[t_name_clean]

    return prize_map, team_rank_map

    return prize_map, team_rank_map

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
