#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

def capture_dashboard():
    """Capture full dashboard showing signal tables with provenance data."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1400})
        
        # Load dashboard
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.wait_for_selector(".container", timeout=10000)
        page.wait_for_timeout(2000)
        
        # Refresh to load live data
        page.get_by_role("button", name="Actualizar").click()
        page.wait_for_timeout(3000)
        
        # Capture full page
        page.screenshot(path=str(ARTIFACTS / "dashboard_full.png"), full_page=True)
        print(f"Saved: {ARTIFACTS}/dashboard_full.png")
        
        # Click on first token to show drawer
        try:
            detail_btns = page.locator("button[data-action='detail']").all()
            if detail_btns:
                detail_btns[0].click()
                page.wait_for_timeout(500)
                page.wait_for_selector("#tokenDrawer.open", timeout=3000)
                page.screenshot(path=str(ARTIFACTS / "drawer_example.png"), full_page=True)
                print(f"Saved: {ARTIFACTS}/drawer_example.png")
        except Exception as e:
            print(f"Drawer capture skipped: {e}")
        
        browser.close()

if __name__ == "__main__":
    print("Capturing dashboard evidence...")
    capture_dashboard()
    print("Done.")
