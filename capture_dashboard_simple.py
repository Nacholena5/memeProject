#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

def capture_dashboard():
    """Capture dashboard showing identity cases."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        
        try:
            # Load dashboard
            print("Loading dashboard...")
            page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(2000)
            
            print("Taking main screenshot...")
            page.screenshot(path=str(ARTIFACTS / "dashboard_full.png"), full_page=True)
            print(f"[OK] {ARTIFACTS}/dashboard_full.png")
            
        except Exception as e:
            print(f"Error: {e}")
            # Still try to capture what loaded
            page.screenshot(path=str(ARTIFACTS / "dashboard_partial.png"), full_page=True)
            print(f"[PARTIAL] {ARTIFACTS}/dashboard_partial.png")
        
        finally:
            browser.close()

if __name__ == "__main__":
    print("Capturing dashboard...")
    capture_dashboard()
    print("Done.")
