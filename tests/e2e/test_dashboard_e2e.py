from __future__ import annotations

import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
ROOT = Path(__file__).resolve().parents[2]


def _server_is_up() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def _apply_scenario(mode: str) -> None:
    subprocess.run(
        [sys.executable, "scripts/set_qa_scenario.py", mode],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module", autouse=True)
def ensure_server_available() -> None:
    if not _server_is_up():
        pytest.skip(f"Dashboard API is not running at {BASE_URL}")


@pytest.fixture
def on_dashboard(page: Page) -> Page:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Panel de decisión de trading")).to_be_visible(timeout=12000)
    return page


def test_dashboard_loads_shell(on_dashboard: Page) -> None:
    expect(on_dashboard.get_by_text("Resumen del sistema")).to_be_visible()
    expect(on_dashboard.locator("#execStatusBadge")).to_be_visible()


def test_full_scenario_renders_signal_tables(page: Page) -> None:
    _apply_scenario("full")
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Actualizar").click()

    expect(page.locator("#topLongBody tr").first).to_be_visible(timeout=12000)
    expect(page.locator("#topShortBody tr").first).to_be_visible(timeout=12000)
    expect(page.locator("#contextEmpty")).to_be_hidden()


def test_partial_scenario_shows_degraded_state(page: Page) -> None:
    _apply_scenario("partial")
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Actualizar").click()

    expect(page.locator("#execStatusBadge")).to_contain_text("Degradado", timeout=12000)
    expect(page.locator("#qualityBadge")).to_contain_text("Degradado", timeout=12000)


def test_empty_scenario_shows_empty_messages(page: Page) -> None:
    _apply_scenario("empty")
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Actualizar").click()

    expect(page.locator("#emptyLong")).to_be_visible(timeout=12000)
    expect(page.locator("#emptyShort")).to_be_visible(timeout=12000)
    expect(page.locator("#performanceEmpty")).to_be_visible(timeout=12000)


def test_connection_failure_banner_appears(page: Page) -> None:
    page.route("**/health", lambda route: route.abort())
    page.route("**/signals/**", lambda route: route.abort())
    page.route("**/market/context", lambda route: route.abort())
    page.route("**/quality/summary", lambda route: route.abort())

    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Actualizar").click()

    expect(page.locator("#backendDownState")).to_be_visible(timeout=12000)
    expect(page.locator("#execStatusBadge")).to_contain_text("Sin conexión")


def test_token_drawer_opens_and_shows_fields(page: Page) -> None:
    _apply_scenario("full")
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Actualizar").click()

    page.locator("button[data-action='detail']").first.click()
    expect(page.locator("#tokenDrawer")).to_have_class(re.compile(r".*open.*"), timeout=12000)
    expect(page.locator("#dLong")).not_to_have_text("-")
    expect(page.locator("#dShort")).not_to_have_text("-")


def test_charts_hide_empty_state_when_data_exists(page: Page) -> None:
    _apply_scenario("full")
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Actualizar").click()

    expect(page.locator("#outcomesEmpty")).to_have_class(re.compile(r".*hidden.*"), timeout=12000)
    expect(page.locator("#metricsEmpty")).to_have_class(re.compile(r".*hidden.*"), timeout=12000)


def test_refresh_updates_last_update_label(page: Page) -> None:
    _apply_scenario("full")
    page.goto(BASE_URL, wait_until="domcontentloaded")

    page.get_by_role("button", name="Actualizar").click()
    expect(page.locator("#lastUpdate")).to_contain_text("Actualizado:", timeout=12000)
