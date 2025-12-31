from src.palkintolaskuri import tallenna_palkintodata
import json
import os

# Generate data
tallenna_palkintodata(json_file="all_results.json", output_file="palkintodata_verified.json")

# Verify
with open("palkintodata_verified.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("\n--- Verification Report ---")
for p in data["prizes"]:
    name = p["nimi"]
    rank = p["sijoitus"]
    cat = p["kategoria"]
    prize = p["individual"]
    team_prize = p["team_share"]
    total = p["total"]
    
    # Print only if they got a prize or top 10
    if prize > 0 or rank <= 10 or total > 0:
        print(f"Name: {name:<30} | Cat: {cat} | Rank: {rank} | Prize: {prize} | Team: {team_prize} | Total: {total}")
