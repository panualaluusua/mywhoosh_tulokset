"""Script to click 'Teams' tab and capture data."""
import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://results.mywhoosh.com/result/a109ae16-d5d7-49cf-8eb7-d5f9414e5b0e"

async def capture_teams():
    async with async_playwright() as p:
        # DEBUG: headless=False so user can see what's happening
        print("Launching browser (visible for debugging)...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        captured_count = 0
        
        async def handle_response(response):
            nonlocal captured_count
            if "json" in response.headers.get("content-type", ""):
                try:
                    text = await response.text()
                    # Check for team specific keywords (must have players so it does not match individual results)
                    if "teamId" in text and "players" in text:
                        data = json.loads(text)
                        
                        # Save each unique response (sometimes categories come in separate chunks)
                        captured_count += 1
                        filename = f"output/captured_team_data_{captured_count}.json"
                        
                        print(f"\n[CAPTURED] Response from {response.url} -> {filename}")
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        
                except:
                    pass

        page.on("response", handle_response)
        
        print("Navigating to URL...")
        await page.goto(URL, timeout=60000)
        
        print("Waiting for page content (max 30s)...")
        try:
            # Wait for meaningful content (e.g. any grid cell or tab)
            # This ensures the App has hydrated
            await page.wait_for_selector('div[class*="MuiGrid"]', timeout=30000) 
            print("Page content detected.")
        except:
             print("Warning: Specific content selector timeout. Page might be empty or using different classes.")
             
        await page.wait_for_timeout(5000)
        
        # Try to find and click "Teams" tab
        print("Looking for Teams tab...")
        # Common selectors for tabs in MUI or standard frameworks
        selectors = [
            "text=Teams", 
            "text=Team Results", 
            "button:has-text('Teams')", 
            "div[role='tab']:has-text('Teams')"
        ]
        
        clicked = False
        for sel in selectors:
            try:
                # Check if it exists and is visible
                count = await page.locator(sel).count()
                if count > 0:
                     print(f"Found candidate for Teams tab: {sel}")
                     if await page.locator(sel).first.is_visible():
                        print(f"Clicking selector: {sel}")
                        await page.locator(sel).first.click()
                        clicked = True
                        break
            except Exception as e:
                print(f"Error checking selector {sel}: {e}")
                
        if clicked:
            print("Clicked Teams tab! Scrolling to load all data...")
            # Scroll multiple times to trigger lazy loading
            for i in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)
        else:
            print("Could not find Teams tab. Dumping page content for debug...")
            try:
                content = await page.content()
                with open("output/debug_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("Saved output/debug_page.html")
            except: pass

        await browser.close()
        
        if captured_count > 0:
            print(f"SUCCESS: Captured {captured_count} data chunks.")
        else:
            print("FAILED: No data captured.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Capture team data from MyWhoosh results page.')
    parser.add_argument('url', nargs='?', help='URL of the results page')
    
    args = parser.parse_args()
    
    target_url = args.url
    if not target_url:
        # Fallback / Default
        target_url = "https://results.mywhoosh.com/result/a109ae16-d5d7-49cf-8eb7-d5f9414e5b0e"
        print(f"No URL provided, using default: {target_url}")
    
    # Update global URL or pass it
    URL = target_url
    
    asyncio.run(capture_teams())
