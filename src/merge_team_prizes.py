"""Script to merge team prizes from captured_team_data*.json into all_results.json."""
import json
import glob
import os
import re

def parse_prize(prize_str):
    if not prize_str: return 0.0
    # "USD 470" or "USD 1,234.56"
    try:
        clean = prize_str.replace("USD", "").replace("\u00a0", "").replace(",", "").strip()
        return float(clean)
    except:
        return 0.0

def merge():
    # 1. Load basic results (individual)
    if not os.path.exists("output/all_results.json"):
        print("output/all_results.json not found")
        return
    
    with open("output/all_results.json", "r", encoding="utf-8") as f:
        all_results = json.load(f)
        
    print(f"Loaded {len(all_results)} individual results.")
    
    # 2. Load all team data files
    team_files = glob.glob("output/captured_team_data*.json")
    print(f"Found team files: {team_files}")
    
    team_prizes_map = {} # { userId: team_share_amount }
    
    for t_file in team_files:
        try:
            with open(t_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Navigate to resultData
            results = []
            category_id = 1 # Hack/Default: most team files are per category, let's try to find it
            
            if isinstance(data, dict):
                if "categoryId" in data:
                    category_id = data["categoryId"]
                
                if "data" in data:
                    results = data["data"].get("resultData", [])
                    if isinstance(data["data"], dict) and "categoryId" in data["data"]:
                        category_id = data["data"]["categoryId"]
                elif "resultData" in data:
                    results = data["resultData"]
            elif isinstance(data, list):
                results = data
                
            print(f"Processing {t_file}: {len(results)} teams. Category: {category_id}")
            
            # Sort teams by rank if available, otherwise assume order
            # Most files are ordered.
            
            for i, team in enumerate(results):
                t_name = team.get("teamName")
                team_rank = team.get("rank")
                if not team_rank:
                    team_rank = i + 1
                    
                prize_str = team.get("prizeMoney", "")
                total_prize = parse_prize(prize_str)
                
                # Jaa potti ja päivitä tulokset
                if total_prize > 0:
                    players = team.get("players", [])
                    
                    # Filter out ANL players from prize sharing
                    valid_players = [
                        p for p in players 
                        if p.get("selectionStatus") != "ANL"
                    ]
                    
                    count = len(valid_players)
                    if count > 0:
                        share = total_prize / count
                        print(f"Team {t_name}: Total {total_prize} -> Share {share} (for {count} valid players out of {len(players)})")
                        
                        for p in valid_players:
                            uid = p.get("userId")
                            
                            # Etsi vastaava rivi tuloksista
                            found = False
                            for row in all_results:
                                if row.get("userId") == uid:
                                    row["teamPrize"] = share
                                    row["teamPrizeTotal"] = total_prize
                                    row["teamRank"] = team_rank
                                    found = True
                                    # Debug
                                    if "Jerry" in row.get("userFullName", "") or "Jenny" in row.get("userFullName", ""):
                                        print(f"  -> Updated {row.get('userFullName')}: share {share}")
                                    break
                            
                            if not found:
                                # JOS AJAAJA PUUTTUU TULOKSISTA (esim. yksilötulokset eivät latautuneet kokonaan)
                                # LISÄTÄÄN HÄNET NYT TIIMIDATAN PERUSTEELLA
                                print(f"  -> WARNING: Rider {p.get('userFullName')} ({uid}) not found in all_results. Injecting...")
                                
                                # Muunna lippu URL -> int jos mahdollista (Suomi = 82)
                                flag_val = p.get("userCountryFlag", "")
                                flag_int = 0
                                if "finland" in str(flag_val).lower():
                                    flag_int = 82
                                elif "sweden" in str(flag_val).lower():
                                    flag_int = 46 # Esimerkki
                                
                                new_entry = {
                                    "userId": uid,
                                    "userFullName": p.get("userFullName", "Unknown"),
                                    "teamName": t_name,
                                    "teamId": team.get("teamId"),
                                    "rank": p.get("rank", 9999),
                                    "categoryId": p.get("categoryId", category_id),
                                    "finishedTime": p.get("finishedTime", 0),
                                    "gapTime": p.get("gapTime", 0),
                                    "selectionStatus": p.get("selectionStatus"),
                                    "userCountryFlag": flag_int, # Tärkeä palkintolaskurille
                                    "userCountryFlagImage": flag_val,
                                    "prizeMoney": None, # Ei yksilöpalkintoa tiedossa täältä
                                    "teamPrize": share,
                                    "teamPrizeTotal": total_prize,
                                    "teamRank": team_rank,
                                    "injected": True # Merkki injektiosta
                                }
                                
                                # Laske sijoitus jos puuttuu
                                if new_entry["rank"] == -1: 
                                    new_entry["rank"] = 9999
                                new_entry["calculated_rank"] = new_entry["rank"]
                                
                                all_results.append(new_entry)
                                print(f"  -> Injected {new_entry['userFullName']} with share {share}")

                                
        except Exception as e:
            print(f"Error reading {t_file}: {e}")

    # 3. Update all_results.json
    updated_count = 0
    for rider in all_results:
        uid = rider.get("userId")
        
        # Check if we have a team share for this user
        if uid in team_prizes_map:
            share = team_prizes_map[uid]
            
            # Store it explicitly
            rider["teamPrize"] = share
            
            # Update 'prizeMoney' string if it was missing or different?
            # User said "Siihen tulee ainoastaan henkilökohtaiset".
            # If we want to show TOTAL, we should add it.
            # But let's verify if 'prizeMoney' already included it?
            # Jerry had $50. Team share of $470/4 = 117.5? Or 470/x?
            
            updated_count += 1
            
    print(f"Updated {updated_count} riders with team prizes.")
    
    with open("output/all_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)
        
    print("Saved output/all_results.json")

if __name__ == "__main__":
    merge()
