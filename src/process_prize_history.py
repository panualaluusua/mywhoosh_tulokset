
import asyncio
import json
import os
import sys
import argparse
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

# Import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import palkintolaskuri
import tietovarasto
# We also use logic from capture_team_data, but we'll integrate it here to avoid spawning too many browsers

# Global storage for parsing session
captured_event_details = None
captured_results = []
captured_team_results = []

def parse_date(date_str):
    """Parses date from various formats returned by API (e.g. '2025-11-02T10:00:00Z') to 'YYYY-MM-DD'."""
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        return date_str
    except:
        return date_str

async def run_capture(url):
    global captured_event_details, captured_results, captured_team_results
    captured_event_details = None
    captured_results = []
    captured_team_results = []
    
    print(f"Opening browser for: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Handler for network responses
        async def handle_response(response):
            global captured_event_details, captured_results, captured_team_results
            
            if response.status != 200: return
            
            try:
                # Optimized filter: Check Content-Type
                ct = response.headers.get("content-type", "")
                if "json" not in ct: return
                
                # Check URL patterns
                url = response.url
                
                # 1. EVENT DETAILS (Metadata + Prize Table)
                # Look for "getEvent" or just "/public/event/" or similar
                # We need Name and Date.
                if "/public/event/" in url and "getEventResult" not in url:
                    data = await response.json()
                    # Validate candidate
                    if "data" in data and ("eventName" in data["data"] or "name" in data["data"] or "prizeMoney" in data["data"]):
                        print(f"  [METADATA] Captured event details from {url}")
                        captured_event_details = data
                        
                # 2. MAIN RESULTS (Individuals)
                if "getEventResult" in url and "gateType" not in url: # Exclude if gateType acts weird, but usually params
                    data = await response.json()
                    # Check if it is really results
                    content = data.get("data", {})
                    if isinstance(content, dict) and "resultData" in content:
                        res = content["resultData"]
                        # Filter out segments (gateType 9=Sprint, 4=KOM usually come separately if tab clicked, 
                        # but sometimes main load has them too? Standard results usually don't have gateType in top records)
                        # We accept all to be safe, filter later.
                        if res:
                             # Just checking first record to guess type
                             if "gateType" in res[0] and res[0]["gateType"] in [4, 9]:
                                 pass # Segment result
                             else:
                                 print(f"  [RESULTS] Captured chunk from {url} ({len(res)} records)")
                                 captured_results.append(data)
                                 
                # 3. TEAM RESULTS (If requested/clicked)
                # Usually captured when "Teams" tab is clicked
                if "teamId" in url or ("getEventResult" in url and "Teams" in url): # Heuristic
                    # Hard to distinguish by URL alone often.
                    # Team data usually has "teamId" in records and "rank" refers to team rank?
                    # We'll check the content
                    data = await response.json()
                    content = data.get("data", {})
                    if "resultData" in content:
                        res = content["resultData"]
                        if res and "members" in res[0]: # Team response often has 'members' or 'players' list
                            print(f"  [TEAMS] Captured team data from {url}")
                            captured_team_results.append(data)
            except:
                pass

        page.on("response", handle_response)

        print("  Navigating...")
        await page.goto(url)
        
        # Wait for initial load
        await page.wait_for_timeout(8000)
        
        # Scroll for lazy loading (Individuals)
        print("  Scrolling for individuals...")
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

        # CHECK IF FINAL -> Click Teams
        # We might not have captured event details yet if they came early. Use what we have.
        is_final = False
        race_name = "Unknown"
        
        if captured_event_details:
             d = captured_event_details.get("data", {})
             race_name = d.get("eventName", d.get("name", "Unknown"))
             if "final" in race_name.lower():
                 is_final = True
        
        # If we didn't get details, we can't be sure, but we can try to click Teams anyway just in case?
        # User said "Use URL... identify if it is final".
        # If we missed details, we might miss the name. 
        # Let's try to click Teams if we see the tab.
        
        print(f"  Race Name detected so far: {race_name}")
        if is_final or race_name == "Unknown":
            print("  Checking for Teams tab (Final or Unknown type)...")
            try:
                teams_tab = page.get_by_text("Teams", exact=False).first
                if await teams_tab.is_visible():
                    print("  Clicking Teams tab...")
                    await teams_tab.click()
                    await page.wait_for_timeout(5000)
                    # Scroll for teams
                    for _ in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
            except:
                print("  Teams tab interaction failed or not found.")

        # --- FALLBACK SCRAPING IF METADATA MISSING ---
        if not captured_event_details:
             print("  [FALLBACK] Attempting to scrape metadata from DOM...")
             try:
                 # 1. Title
                 page_title = await page.title()
                 print(f"  Page Title: {page_title}")
                 
                 # 2. H1 / Event Name
                 # Try common selectors
                 h1_text = ""
                 h1 = page.locator("h1").first
                 if await h1.count() > 0:
                     h1_text = await h1.text_content()
                     
                 # Try H2 if H1 is generic or empty
                 if not h1_text or "MYWHOOSH" in h1_text.upper():
                      h2 = page.locator("h2").first
                      if await h2.count() > 0:
                          h2_text = await h2.text_content()
                          if h2_text and len(h2_text) > 3:
                               h1_text = h2_text # Prefer H2
                               print(f"  H2 Text (preferred): {h1_text}")
                     
                 print(f"  Name Candidate: {h1_text}")
                     
                 # 3. Date
                 # Often near the title
                 date_text = ""
                 # Try to find date-like text in the header section
                 # This is tricky without knowing the exact DOM, but we can try generic text search?
                 # Or just rely on Title/H1.
                 
                 # Construct valid-ish details object
                 captured_event_details = {
                     "data": {
                         "eventName": h1_text or page_title or "Unknown Scraped Race",
                         "startTime": datetime.now().strftime("%Y-%m-%d"), # Default to now if not found, user can edit CSV
                         "scraped": True
                     }
                 }
                 # Try to find date in text content
                 content = await page.content()
                 # Simple regex for date?
                 # Ignoring for now to keep it simple, Name is most important for "Final" detection.
             except Exception as e:
                 print(f"  Scraping failed: {e}")

        await browser.close()

    return captured_event_details, captured_results, captured_team_results

def process_url(url):
    print(f"\n--- Processing: {url} ---")
    
    # 1. CAPTURE
    details, results, teams = asyncio.run(run_capture(url))
    
    # 2. ANALYZE & PREPARE DATA
    if not details:
        print("!! WARNING: Could not capture Event Details (Name/Date). Using timestamp/id.")
        # Try to extract ID from URL
        if "eventId=" in url:
             event_id = url.split("eventId=")[1].split("&")[0]
        elif "/result/" in url:
             event_id = url.split("/result/")[1].split("/")[0].split("?")[0]
        else:
             event_id = "UnknownID"
             
        race_name = "Unknown Race"
        race_date = datetime.now().strftime("%Y-%m-%d")
        
        # Try to save what we have
        prizes_data = {} # No currency conversion data
    else:
        d = details.get("data", {})
        # Scraped data structure validation
        if "scraped" in d:
             race_name = d.get("eventName", "Unknown Scraped Race")
             # Try to clean up name 'MYWHOOSH EVENT RESULTS' if likely generic
             if "MYWHOOSH" in race_name.upper() and "RESULTS" in race_name.upper():
                  # Maybe H2 was better?
                   pass
        else:
             race_name = d.get("eventName", d.get("name", "Unknown Race"))
             
        raw_date = d.get("startTime", d.get("eventStartdate", "")) # Try common keys
        race_date = parse_date(raw_date)
        
        # ID might be in details (scraped) or we extract from URL
        event_id = d.get("id")
        if not event_id:
             if "eventId=" in url:
                 event_id = url.split("eventId=")[1].split("&")[0]
             elif "/result/" in url:
                 event_id = url.split("/result/")[1].split("/")[0].split("?")[0]
             else:
                 event_id = "UnknownID"

        # Save event_details.json for palkintolaskuri to use (it reads from file)
        with open("output/event_details.json", "w", encoding="utf-8") as f:
            json.dump(details, f, indent=4)
            
    is_final = "final" in race_name.lower()
    print(f"  Name: {race_name}")
    print(f"  Date: {race_date}")
    print(f"  Type: {'FINAL' if is_final else 'Qualifier/Other'}")
    
    # 3. SAVE RESULTS TO FILE (for scripts to pick up)
    # Aggregate results
    all_riders = []
    seen = set()
    for chunk in results:
        # Standardize extraction
        recs = []
        if "data" in chunk and "resultData" in chunk["data"]: recs = chunk["data"]["resultData"]
        
        for r in recs:
            uid = r.get("userId")
            if uid and uid not in seen:
                seen.add(uid)
                all_riders.append(r)
                
    # Create rank (needed for palkintolaskuri) - simplified logic here or reuse `hae_tulokset`'s logic?
    # Reuse is better but `hae_tulokset` is Main script.
    # We will reconstruct basic list and let `palkintolaskuri` do the heavy lifting?
    # actually `palkintolaskuri` expects `calculated_rank`. 
    # Let's save to `output/all_results.json` ensuring ranks are present.
    
    if not all_riders:
        print("!! ERROR: No individual results captured. Skipping.")
        return

    # Sort & Rank (Minimal logic to support tool)
    df = pd.DataFrame(all_riders)
    if "finishedTime" in df.columns:
         df['time_ms'] = pd.to_numeric(df['finishedTime'], errors='coerce').fillna(9999999999)
    else:
         df['time_ms'] = 9999999999
         
    df.sort_values(by=['categoryId', 'time_ms'], inplace=True)
    
    # Rank
    df['calculated_rank'] = df.groupby('categoryId').cumcount() + 1
    # Note: We skip the ANL logic for now to keep it simple, or replicate it?
    # Replicate simple ANL check
    if 'selectionStatus' in df.columns:
        mask = df['selectionStatus'] != 'ANL'
        df.loc[mask, 'calculated_rank'] = df[mask].groupby('categoryId').cumcount() + 1
        df.loc[~mask, 'calculated_rank'] = 0
    
    # Save
    all_res_data = df.to_dict('records')
    with open("output/all_results.json", "w", encoding="utf-8") as f:
        json.dump(all_res_data, f, indent=4, default=str)
        
    # 4. PROCESS TEAMS (If Final)
    if is_final and teams:
        # Save team chunks
        for i, t_chunk in enumerate(teams):
            with open(f"output/captured_team_data_{i+1}.json", "w", encoding="utf-8") as f:
                json.dump(t_chunk, f, indent=4)
        
        # Run merge
        print("  Merging team prizes...")
        # We need to import the script logic dynamically or run via subprocess?
        # `merge_team_prizes` is simple enough to import if we restructured, but it has `if name==main`.
        # Let's run it via os.system / subprocess to ensure clean state
        os.system("python src/merge_team_prizes.py > NUL") # Suppress output

    # 5. CALCULATE & SAVE PRIZES
    print("  Calculating prizes...")
    # palkintolaskuri.tallenna_palkintodata writes to output/palkintodata.json
    palkintolaskuri.tallenna_palkintodata(
        json_file="output/all_results.json",
        output_file="output/palkintodata.json",
        race_name=race_name,
        race_date=race_date,
        event_id=event_id
    )
    
    # 6. UPDATE WAREHOUSE
    print("  Updating storage (CSV)...")
    tietovarasto.tallenna_kisa_csv(
        race_date=race_date,
        race_name=race_name,
        palkinto_json="output/palkintodata.json",
        event_id=event_id
    )
    print("  Done.")

def main():
    parser = argparse.ArgumentParser(description="Batch process MyWhoosh race URLs.")
    parser.add_argument('input_file', nargs='?', help="File containing URLs (one per line)")
    args = parser.parse_args()
    
    urls = []
    if args.input_file and os.path.exists(args.input_file):
        with open(args.input_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        print("Enter URLs (one per line). Paste headers or empty line to finish:")
        while True:
            try:
                line = input()
                if not line: break
                if line.startswith("http"):
                    urls.append(line.strip())
            except EOFError:
                break
                
    print(f"\nLoaded {len(urls)} URLs to process.\n")
    
    for url in urls:
        try:
            process_url(url)
        except Exception as e:
            print(f"!! ERROR processing {url}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
