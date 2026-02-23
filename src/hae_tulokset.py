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
    print(f"DEBUG: Response from {response.url} (Status: {response.status})")
    if "/public/event/" in response.url and "getEventResult" not in response.url and response.status == 200:
        try:
            json_data = await response.json()
            # Verify it has prizeMoney
            if "data" in json_data and "prizeMoney" in json_data["data"]:
                print(f"Intercepted Event Details from: {response.url}")
                event_details = json_data
                with open('output/event_details.json', 'w', encoding='utf-8') as f:
                    json.dump(event_details, f, indent=4)
                print("Saved output/event_details.json")
        except Exception as e:
            pass

    # Check if this is the API call we are looking for (Results)
    # Match URL OR Content-Type + Keywords (more robust)
    is_target_api = ("getEventResult" in response.url or "getEventResults" in response.url)
    if is_target_api and response.status == 200:
        print(f"Intercepted API response from: {response.url}")
        try:
            json_data = await response.json()
            
            # Check if this is main results or segment results
            # Segment results usually have 'gateType' in the first record
            is_segment = False
            if "data" in json_data and isinstance(json_data["data"], dict) and "resultData" in json_data["data"]:
                res_data = json_data["data"]["resultData"]
                if len(res_data) > 0 and "gateType" in res_data[0]:
                    g_type = res_data[0]["gateType"]
                    if g_type == 9:

                        print("Captured SPRINT results.")
                        with open('output/sprint_results.json', 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=4)
                        is_segment = True
                    elif g_type == 4:
                        print("Captured KOM results.")
                        with open('output/kom_results.json', 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=4)
                        is_segment = True

            if not is_segment:
                # Store all main result candidates
                if captured_data is None:
                    captured_data = []
                captured_data.append(json_data)
                print(f"Captured candidate MAIN JSON data. Total candidates: {len(captured_data)}")

                
        except Exception as e:
            print(f"Failed to parse JSON: {e}")

    # Fallback: Check GENERIC json responses for key data if strict URL match missed it
    elif "json" in response.headers.get("content-type", "") and response.status == 200:
         try:
            # Don't await text() if it's huge, but for results it should be fine
            # We filter by URL to avoid reading ALL traffic
            if "mywhoosh.com" in response.url:
                text = await response.text()
                if "prizeMoney" in text and "gateType" in text and "resultData" in text:
                     print(f"Fallback Intercept from: {response.url}")
                     json_data = json.loads(text)
                     if captured_data is None:
                        captured_data = []
                     captured_data.append(json_data)
                     print(f"Captured candidate MAIN JSON data (via fallback). Total: {len(captured_data)}")
         except: pass

async def run(url, show_all=False):
    global captured_data
    
    # Clean up old event details to ensure we get fresh ones
    import os
    if os.path.exists('output/event_details.json'):
        try:
            os.remove('output/event_details.json')
            print("Deleted old output/event_details.json to ensure fresh capture.")
        except: pass
        
    async with async_playwright() as p:
        print("Launching browser (visible for debugging)...")
        browser = await p.chromium.launch(headless=False)
        # Use a realistic User-Agent to avoid detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Subscribe to response events
        page.on("response", handle_response)

        print(f"Navigating to {url}...")
        await page.goto(url)

        # Wait for data to be captured (timeout after 60s)
        print("Waiting for API response...")
        
        # Wait for initial load
        print("Waiting for page load state 'networkidle' (max 30s)...")
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            print("Warning: Network idle timeout, continuing anyway...")
            
        await page.wait_for_timeout(10000)
        
        # Try to find and click tabs to fetch Segment Data
        print("Looking for Sprint/KOM tabs...")
        try:
            # Sprint
            sprint_tab = page.get_by_text("Sprint", exact=False).first
            if await sprint_tab.count() > 0:
                print("Clicking Sprint tab...")
                await sprint_tab.click()
                print("Waiting for Sprint data (5s)...")
                await page.wait_for_timeout(5000)
            
            # KOM
            kom_tab = page.get_by_text("KOM", exact=False).first
            if await kom_tab.count() == 0:
                kom_tab = page.get_by_text("King of the Mountain", exact=False).first
            
            if await kom_tab.count() > 0:
                print("Clicking KOM tab...")
                await kom_tab.click()
                print("Waiting for KOM data (5s)...")
                await page.wait_for_timeout(5000)
            else:
                print("KOM tab not found.")
                
        except Exception as e:
            print(f"Error interacting with tabs: {e}")

        for _ in range(60):
            if captured_data:
                break
            await asyncio.sleep(0.5)
        
        if not captured_data:
            print("Timeout: Did not receive the expected API response via internal capture.")
            print("Checking for pre-captured data from capture_team_data.py...")
            
            import glob
            files = glob.glob("output/captured_team_data_*.json")
            if files:
                captured_data = []
                for fpath in files:
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            jd = json.load(f)
                            captured_data.append(jd)
                        print(f"Loaded fallback data from: {fpath}")
                    except Exception as e:
                        print(f"Failed to load fallback {fpath}: {e}")
            
            if not captured_data:
                await browser.close()
                return []


        # ITERATE OVER CATEGORIES
        print("Looking for Category dropdown to load all categories...")
        try:
            # First, check if there's a combobox or div that acts as select
            select_box = page.locator("div.MuiSelect-select, div[role='combobox'], div[role='button']:has-text('Category')").first
            
            # If not found, try text match
            if await select_box.count() == 0:
                 select_box = page.get_by_text("Category", exact=False).first
            
            if await select_box.is_visible():
                print("Found Category dropdown. Analyzing options...")
                await select_box.click(force=True)
                await page.wait_for_timeout(2000)
                
                options = page.get_by_role("option")
                count = await options.count()
                print(f"Found {count} categories.")
                
                # Close dropdown initially
                await page.mouse.click(0, 0)
                await page.wait_for_timeout(1000)
                
                for i in range(count):
                    # Open dropdown
                    await select_box.click(force=True)
                    await page.wait_for_timeout(1000)
                    
                    # Select option
                    opt = page.get_by_role("option").nth(i)
                    print(f"Selecting category {i+1}...")
                    await opt.click(force=True)
                    await page.wait_for_timeout(4000) # Wait for network / API
                    
                    # Scroll for THIS category to trigger lazy load
                    for _ in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1500)
            else:
                print("Could not find a recognizable Category dropdown. Falling back to default.")
        except Exception as e:
            print(f"Error interacting with categories: {e}")

        # Try to scroll a few more times anyway
        print("Final scrolling to ensure all results are loaded...")
        for i in range(8): # Scroll multiple times
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
        await browser.close()
        
        # Process the captured data
        # Aggregate ALL captured chunks
        
        raw_list = []
        seen_ids = set()
        
        if captured_data and isinstance(captured_data, list):
             print(f"Processing {len(captured_data)} captured chunks...")
             for chunk in captured_data:
                # Extract records from this chunk
                chunk_records = []
                if isinstance(chunk, dict):
                    if 'data' in chunk:
                         content = chunk['data']
                         if isinstance(content, dict) and 'resultData' in content:
                             chunk_records = content['resultData']
                         elif isinstance(content, list):
                             chunk_records = content
                    elif 'results' in chunk:
                         chunk_records = chunk['results']
                    else:
                         # Direct list?
                         chunk_records = [chunk] # Unlikely but safe
                
                # Add unique records
                for record in chunk_records:
                    # Use unique identifier (userId or similar)
                    uid = record.get('userId')
                    if not uid:
                         # Fallback to random ID if missing
                         uid = str(record) 
                    
                    if uid not in seen_ids:
                        seen_ids.add(uid)
                        raw_list.append(record)
                        
             print(f"Total aggregated unique records: {len(raw_list)}")

        else:
             print("No data captured.")
             return []

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
                'time_ms': time_ms,
                'prizeMoney': record.get('prizeMoney', '-') # Tärkeä: Ota talteen API:n palkintotieto
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
        print("Saving all results to output/all_results.json...")
        # Convert back to list of dicts for JSON dumping, including calculated rank
        all_results_export = []
        for index, row in df_all.iterrows():
            record = row['raw']
            record['calculated_rank'] = int(row['calculated_rank'])
            all_results_export.append(record)
            
        with open('output/all_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_results_export, f, indent=4, default=str)
        print("Saved output/all_results.json")

        # Now filter for Finnish riders (ID 82 or by flag URL)
        finnish_riders = []
        
        for index, row in df_all.iterrows():
            record = row['raw']
            flag_val = record.get('userCountryFlag', '')
            flag_img = str(record.get('userCountryFlagImage', '')).lower()
            
            if flag_val == 82 or 'finland' in flag_img:
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

    with open('output/results.md', 'w', encoding='utf-8') as f:
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
    
    print("Results written to output/results.md")

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
        if not data:
            print("VIRHE: Tulosten haku epäonnistui (ei dataa tai timeout).")
            exit(1)
            
        process_results(data, args.all)
        
        print("\nTulokset haettu ja tallennettu output/all_results.json tiedostoon.")
        print("Huom: Grafiikoiden ja raporttien luonti tapahtuu erillisessä vaiheessa putkea.")

            
    except Exception as e:
        print(f"\nVirhe ohjelman suorituksessa: {e}")

    print("\nValmis!")
    print("\nValmis!")
    # input("Paina Enter sulkeaksesi ikkunan...") # Poistettu, jotta bat-tiedosto jatkaa heti
