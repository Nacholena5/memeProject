from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def _is_hidden(page, selector: str) -> bool:
    cls = page.locator(selector).get_attribute("class") or ""
    return "hidden" in cls.split()


def capture(base_url: str, image_path: Path, report_path: Path) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1800, "height": 2200})
        page.goto(base_url, wait_until="domcontentloaded")
        page.get_by_role("button", name="Actualizar").click()
        page.wait_for_timeout(2500)

        report = {
            "backendDownHidden": _is_hidden(page, "#backendDownState"),
            "globalStatus": page.locator("#execStatusBadge").inner_text().strip(),
            "summaryBias": page.locator("#execBias").inner_text().strip(),
            "summaryRisk": page.locator("#execRisk").inner_text().strip(),
            "marketBtc": page.locator("#ctxBtc").inner_text().strip(),
            "marketSol": page.locator("#ctxSol").inner_text().strip(),
            "marketMeme": page.locator("#ctxMeme").inner_text().strip(),
            "marketLiquidity": page.locator("#ctxLiq").inner_text().strip(),
            "qualityBadge": page.locator("#qualityBadge").inner_text().strip(),
            "qualitySignals": page.locator("#qualitySignals").inner_text().strip(),
            "qualityOutcomes": page.locator("#qualityOutcomes").inner_text().strip(),
            "qualityMetrics": page.locator("#qualityMetrics").inner_text().strip(),
            "longRows": page.locator("#topLongBody tr").count(),
            "shortRows": page.locator("#topShortBody tr").count(),
            "outcomesEmptyHidden": _is_hidden(page, "#outcomesEmpty"),
            "metricsEmptyHidden": _is_hidden(page, "#metricsEmpty"),
            "contextEmptyHidden": _is_hidden(page, "#contextEmpty"),
            "lastUpdate": page.locator("#lastUpdate").inner_text().strip(),
        }

        page.screenshot(path=str(image_path), full_page=True)
        report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
        browser.close()

    print(str(image_path))
    print(str(report_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture dashboard screenshot + DOM state report")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--image", default=str(ARTIFACTS / "dashboard_postfix.png"))
    parser.add_argument("--report", default=str(ARTIFACTS / "dashboard_postfix_report.json"))
    args = parser.parse_args()
    capture(base_url=args.base_url, image_path=Path(args.image), report_path=Path(args.report))
