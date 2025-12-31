import argparse
import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright

# Global variable to store the captured data
captured_data = None
event_details = None

async def handle_response(response):
    global captured_data, event_details
    
    # Capture Event Details (Prize Money)
    if "/public/event/" in response.url and "getEventResult" not in response.url and response.status == 200:
        try:
            json_data = await response.json()
            # Verify it has prizeMoney
            if "data" in json_data and "prizeMoney" in json_data["data"]:
                print(f"Intercepted Event Details from: {response.url}")
                event_details = json_data
                with open('event_details.json', 'w', encoding='utf-8') as f:
                    json.dump(event_details, f, indent=4)
                print("Saved event_details.json")
        except Exception as e:
            pass

    # Check if this is the API call we are looking for (Results)
    if "getEventResult" in response.url and response.status == 200:
        print(f"Intercepted API response from: {response.url}")
        try:
            json_data = await response.json()
            
            # Check if this is main results or segment results
            # Segment results usually have 'gateType' in the first record
            is_segment = False
            if "data" in json_data and "resultData" in json_data["data"]:
                res_data = json_data["data"]["resultData"]
                if len(res_data) > 0 and "gateType" in res_data[0]:
                    g_type = res_data[0]["gateType"]
                    if g_type == 9:
                        print("Captured SPRINT results.")
                        with open('sprint_results.json', 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=4)
                        is_segment = True
                    elif g_type == 4:
                        print("Captured KOM results.")
                        with open('kom_results.json', 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=4)
                        is_segment = True

            if not is_segment:
                captured_data = json_data
                print("Successfully captured MAIN JSON data.")
                
        except Exception as e:
            print(f"Failed to parse JSON: {e}")

async def run(url, show_all=False):
    global captured_data
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Subscribe to response events
        page.on("response", handle_response)

        print(f"Navigating to {url}...")
        await page.goto(url)

        # Wait for data to be captured (timeout after 30s)
        print("Waiting for API response...")
        
        # Wait for initial load
        await page.wait_for_timeout(5000)
        
        # Try to find and click tabs to fetch Segment Data
        print("Looking for Sprint/KOM tabs...")
        try:
            # Sprint
            sprint_tab = page.get_by_text("Sprint", exact=False).first
            if await sprint_tab.count() > 0:
                print("Clicking Sprint tab...")
                await sprint_tab.click()
                await page.wait_for_timeout(3000)
            
            # KOM
            kom_tab = page.get_by_text("KOM", exact=False).first
            if await kom_tab.count() == 0:
                kom_tab = page.get_by_text("King of the Mountain", exact=False).first
            
            if await kom_tab.count() > 0:
                print("Clicking KOM tab...")
                await kom_tab.click()
                await page.wait_for_timeout(3000)
            else:
                print("KOM tab not found.")
                
        except Exception as e:
            print(f"Error interacting with tabs: {e}")

        for _ in range(60):
            if captured_data:
                break
            await asyncio.sleep(0.5)
        
        if not captured_data:
            print("Timeout: Did not receive the expected API response.")
            await browser.close()
            return []

        await browser.close()
        
        # Process the captured data
        # We need to inspect the structure. Based on typical responses:
        # It might be a list of riders, or a dict with a 'data' key.
        
        riders = []
        raw_list = []
        
        if isinstance(captured_data, list):
            print(f"Debug: Root is list with {len(captured_data)} items.")
            raw_list = captured_data
        elif isinstance(captured_data, dict):
            print(f"Debug: Root is dict with keys: {captured_data.keys()}")
            if 'data' in captured_data:
                data_content = captured_data['data']
                if isinstance(data_content, list):
                    raw_list = data_content
                elif isinstance(data_content, dict):
                    print(f"Debug: 'data' is a dict with keys: {data_content.keys()}")
                    # It seems 'data' contains categories as keys. Flatten the values into one list.
                    for key, val in data_content.items():
                        if isinstance(val, list):
                            print(f"Debug: Key '{key}' has {len(val)} items.")
                            raw_list.extend(val)
                        elif isinstance(val, dict):
                             # Maybe nested further?
                             pass
            elif 'results' in captured_data:
                raw_list = captured_data['results']
            else:
                raw_list = [captured_data]

        print(f"Processing {len(raw_list)} records...")
        
        if len(raw_list) > 0:
             print(f"Debug: First record keys: {raw_list[0].keys()}")

        # Process all riders to calculate ranks
        all_riders = []
        
        for record in raw_list:
            # Extract necessary fields for ranking
            category = record.get('categoryId', 'Unknown')
            time_ms = record.get('finishedTime', 0)
            
            # Skip invalid times if necessary, or handle DNF
            if time_ms == 0:
                time_ms = 999999999 # Push to end
            
            all_riders.append({
                'raw': record,
                'category': category,
                'time_ms': time_ms
            })

        # Convert to DataFrame for easy sorting and ranking
        df_all = pd.DataFrame(all_riders)
        
        if df_all.empty:
            return []

        # Sort by Category and Time
        df_all = df_all.sort_values(by=['category', 'time_ms'])
        
        # Calculate Rank within Category, EXCLUDING ANL riders
        # First, identify valid riders
        # selectionStatus might be in 'raw' dict inside the row, but we didn't extract it to top level col yet.
        # Let's extract it for easier filtering.
        df_all['selection_status'] = df_all['raw'].apply(lambda x: x.get('selectionStatus'))
        
        # Create a mask for valid riders (not ANL)
        valid_mask = df_all['selection_status'] != 'ANL'
        
        # Calculate rank only for valid riders
        df_all.loc[valid_mask, 'calculated_rank'] = df_all[valid_mask].groupby('category').cumcount() + 1
        
        # Assign 0 or similar to ANL riders
        df_all.loc[~valid_mask, 'calculated_rank'] = 0
        
        # Fill NaN if any (shouldn't be for valid rows)
        df_all['calculated_rank'] = df_all['calculated_rank'].fillna(0).astype(int)
        
        # Save all results to JSON as requested
        print("Saving all results to all_results.json...")
        # Convert back to list of dicts for JSON dumping, including calculated rank
        all_results_export = []
        for index, row in df_all.iterrows():
            record = row['raw']
            record['calculated_rank'] = int(row['calculated_rank'])
            all_results_export.append(record)
            
        with open('all_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_results_export, f, indent=4, default=str)
        print("Saved all_results.json")

        # Now filter for Finnish riders (ID 82)
        finnish_riders = []
        
        for index, row in df_all.iterrows():
            record = row['raw']
            if record.get('userCountryFlag') == 82:
                name = record.get('userFullName', 'Unknown')
                # Use the calculated rank
                rank = row['calculated_rank']
                
                time_ms = row['time_ms']
                if time_ms >= 999999999:
                    time_str = "DNF"
                else:
                    seconds = (time_ms / 1000)
                    m, s = divmod(seconds, 60)
                    h, m = divmod(m, 60)
                    time_str = "{:d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

                rider = {
                    'rank': rank,
                    'name': name,
                    'category': row['category'],
                    'time': time_str,
                    'team': record.get('teamName', '-'),
                    'avg_power': record.get('avgPower', '-'),
                    'avg_hr': record.get('avgHeartRate', '-'),
                    'wkg': record.get('wattPerKG', '-'),
                    'raw': record
                }
                finnish_riders.append(rider)

        return finnish_riders

def process_results(results, show_all):
    if not results:
        print("No Finnish riders found.")
        return

    df = pd.DataFrame(results)
    
    # Group by Category
    grouped = df.groupby('category')

    with open('results.md', 'w', encoding='utf-8') as f:
        f.write(f"# MyWhoosh Tulokset (Suomalaiset)\n\n")

        for name, group in grouped:
            f.write(f"## Kategoria: {name}\n\n")
            
            # Sort by rank
            group = group.sort_values('rank')

            display_group = group
            if not show_all:
                display_group = group.head(15)
            
            # Markdown Table
            f.write(f"| Sijoitus | Nimi | Aika | Tiimi |\n")
            f.write(f"|---|---|---|---|\n")
            
            for index, row in display_group.iterrows():
                f.write(f"| {row['rank']} | {row['name']} | {row['time']} | {row['team']} |\n")
            
            if not show_all and len(group) > 15:
                f.write(f"\n... ja {len(group) - 15} muuta.\n")
            f.write("\n")
    
    print("Results written to results.md")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hae MyWhoosh-tulokset suomalaisille.')
    parser.add_argument('input', nargs='?', help='Tapahtuman URL tai Event ID')
    parser.add_argument('--all', action='store_true', help='Näytä kaikki tulokset (ei vain Top 15)')
    parser.add_argument('--name', help='Kisan nimi (esim. "MYWHOOSH SUNDAY RACE")')
    parser.add_argument('--date', help='Kisan pvm (esim. "1.12.2025")')
    parser.add_argument('--final', action='store_true', help='Laske tiimipalkinnot (Finaali)')
    
    args = parser.parse_args()
    
    target_input = args.input
    race_name = args.name
    race_date = args.date
    is_final = args.final
    
    if not target_input:
        print("--- MyWhoosh Tuloshaku ---")
        target_input = input("Anna tapahtuman URL tai Event ID: ").strip()
        
        if not race_name:
             race_name = input("Anna kisan nimi (valinnainen, paina Enter ohittaaksesi): ").strip()
        
        if not race_date:
             race_date = input("Anna kisan pvm (valinnainen, paina Enter ohittaaksesi): ").strip()
             
        if not is_final:
            final_input = input("Onko kyseessä Finaali (lasketaanko tiimipalkinnot)? (k/E): ").strip().lower()
            if final_input in ['k', 'y', 'kyllä', 'yes']:
                is_final = True
            else:
                is_final = False
    
    if not target_input:
        print("Ei syötettä. Lopetetaan.")
        input("Paina Enter lopettaaksesi...")
        exit()

    # Determine URL
    if "http" in target_input:
        url = target_input
    else:
        # Assume Event ID
        # Clean up if they pasted "eventId=..."
        if "eventId=" in target_input:
            event_id = target_input.split("eventId=")[1].split("&")[0]
        else:
            event_id = target_input
        
        url = f"https://results.mywhoosh.com/complete-result?eventId={event_id}"
    
    print(f"\nHaetaan tuloksia osoitteesta: {url}")
    print("Tämä voi kestää hetken (käynnistetään selainta...)\n")
    
    try:
        data = asyncio.run(run(url, args.all))
        process_results(data, args.all)
        
        # Generate graphics
        print("\nLuodaan grafiikat...")
        try:
            from luo_grafiikat import create_images
            create_images("all_results.json", race_name, race_date, is_final)
            
            # Generate text report
            print("\nLuodaan tulosraportti (tulokset.txt)...")
            from palkintolaskuri import save_results_report, tallenna_palkintodata
            save_results_report("all_results.json", "tulokset.txt")
            
            # Save intermediate prize data
            print("\nLasketaan ja tallennetaan palkintodata (palkintodata.json)...")
            
            # Extract EventID
            event_id = "Unknown"
            if data and len(data) > 0:
                # data contains rider dicts, original json is in 'raw'
                if 'raw' in data[0]:
                    event_id = data[0]['raw'].get('eventId', 'Unknown')
                else:
                    # Fallback if structure is different
                    event_id = data[0].get('eventId', 'Unknown')
            
            tallenna_palkintodata("all_results.json", "palkintodata.json", race_name, race_date, event_id)
            
            print("\nPalkintodata valmis. Aja 'python src/paivita_varasto.py' tallentaaksesi palkinnot tietovarastoon.")
            
        except Exception as e:
            print(f"Virhe grafiikoiden/raportin/palkintodatan luonnissa: {e}")
            
        except Exception as e:
            print(f"Virhe grafiikoiden/raportin luonnissa: {e}")
            
    except Exception as e:
        print(f"\nVirhe ohjelman suorituksessa: {e}")

    print("\nValmis!")
    print("\nValmis!")
    # input("Paina Enter sulkeaksesi ikkunan...") # Poistettu, jotta bat-tiedosto jatkaa heti
