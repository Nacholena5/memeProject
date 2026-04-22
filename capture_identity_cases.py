#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

# The 3 cases we want to capture
CASES = {
    "confirmed": {"symbol": "SOLAR", "address_start": "So1ar4E"},
    "inferred": {"symbol": "BOME", "address_start": "ukHH6c7"},
    "unverified": {"symbol": "TOKEN", "address_start": "Fh3hFf3"},
}

def capture_case(case_name: str, case_info: dict) -> None:
    """Capture a token row and its drawer."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible for demo
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(BASE_URL, wait_until="domcontentloaded")
        
        # Wait for page to load and refresh
        page.wait_for_selector("#topLongBody", timeout=10000)
        page.get_by_role("button", name="Actualizar").click()
        page.wait_for_timeout(3000)
        
        # Find the row with our symbol
        symbol = case_info["symbol"]
        address_start = case_info["address_start"]
        
        try:
            # Look for the token in the tables
            rows = page.locator("table tr").all()
            target_row = None
            for row in rows:
                if symbol in row.inner_text():
                    target_row = row
                    break
            
            if not target_row:
                print(f"  WARNING: {symbol} not found in tables")
                browser.close()
                return
            
            # Screenshot of the row before clicking
            print(f"Capturing row: {symbol}")
            row_bbox = target_row.bounding_box()
            page.screenshot(path=str(ARTIFACTS / f"01_row_{case_name}.png"))
            
            # Click detail button to open drawer
            detail_btn = target_row.locator("button[data-action='detail']")
            detail_btn.click()
            page.wait_for_timeout(500)
            
            # Wait for drawer to open
            drawer = page.locator("#tokenDrawer")
            drawer.wait_for(state="visible", timeout=5000)
            page.wait_for_timeout(500)
            
            # Full page screenshot with drawer open
            print(f"Capturing drawer: {symbol}")
            page.screenshot(path=str(ARTIFACTS / f"02_drawer_{case_name}.png"))
            
            # Capture drawer content as JSON
            drawer_data = {
                "symbol": page.locator("#dSymbol").inner_text().strip(),
                "name": page.locator("#dName").inner_text().strip(),
                "address": page.locator("#dAddress").inner_text().strip(),
                "address_full": page.locator("#dAddressFull").inner_text().strip() if page.locator("#dAddressFull").is_visible() else "N/A",
                "pair": page.locator("#dPair").inner_text().strip(),
                "metadata_source": page.locator("#dMetaSource").inner_text().strip(),
                "metadata_confidence": page.locator("#dMetaConf").inner_text().strip(),
                "last_source": page.locator("#dLastSource").inner_text().strip(),
                "last_validated": page.locator("#dLastValidated").inner_text().strip(),
                "conflict": page.locator("#dConflict").inner_text().strip(),
                "decision": page.locator("#dDecision").inner_text().strip(),
            }
            
            # Save drawer content
            with open(ARTIFACTS / f"03_data_{case_name}.json", "w") as f:
                json.dump(drawer_data, f, indent=2)
            
            print(f"✓ {case_name}: {drawer_data['symbol']} - {drawer_data['metadata_confidence']}")
            
        except Exception as e:
            print(f"  ERROR capturing {case_name}: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    print("Capturing identity cases...")
    for case_name, case_info in CASES.items():
        print(f"\n### {case_name.upper()} ###")
        capture_case(case_name, case_info)
    
    print("\n✓ All captures complete in:", ARTIFACTS)
