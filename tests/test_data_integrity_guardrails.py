from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.api import routes_scanner
from app.services.playbook_scanner_service import watchlist_today_payload
from tests.data_integrity_fixtures import (
    create_completed_session,
    seed_demo_data,
    seed_fallback_identities,
    seed_historical_data,
    seed_live_data_valid,
    seed_stale_data,
    seed_synthetic_data,
)


def _all_watch_rows(payload: dict) -> list[dict]:
    return [
        *payload.get("strong", []),
        *payload.get("priority", []),
        *payload.get("secondary", []),
        *payload.get("short_paper", []),
    ]


def test_case_a_current_session_empty_with_historical_valid(isolated_scanner_repo) -> None:
    repo = isolated_scanner_repo
    now = datetime.now(UTC)

    historical_session_id = seed_historical_data(repo, now)
    create_completed_session(
        repo,
        started_at=now - timedelta(minutes=30),
        finished_at=now - timedelta(minutes=3),
        degraded=False,
        watchlist_count=0,
        discarded_count=0,
        notes={"seed_type": "current_empty"},
    )

    payload = watchlist_today_payload()

    assert payload["is_live"] is False
    assert payload["total"] == 0
    assert payload["strong"] == []
    assert payload["current_session"] is None
    assert payload["latest_valid_available"] is True
    assert payload["latest_valid_session"]["scan_session_id"] == historical_session_id
    assert payload["latest_valid_session"]["source"] == "latest_valid"


def test_case_b_only_fallback_or_unverified_not_operable(isolated_scanner_repo) -> None:
    repo = isolated_scanner_repo
    now = datetime.now(UTC)

    seed_fallback_identities(repo, now)
    payload = watchlist_today_payload()
    rows = _all_watch_rows(payload)

    assert payload["strong"] == []
    assert rows
    assert all(row["data_origin"] == "fallback" for row in rows)
    assert all(row["operability_status"] != "operable" for row in rows)

    funnel_payload = routes_scanner.funnel_latest()
    assert funnel_payload["steps"]["operable"] == 0


def test_case_c_demo_and_synthetic_do_not_contaminate_main_flow(isolated_scanner_repo) -> None:
    repo = isolated_scanner_repo
    now = datetime.now(UTC)

    seed_live_data_valid(repo, now)
    seed_demo_data(repo, now)
    seed_synthetic_data(repo, now)

    payload = watchlist_today_payload()
    rows = _all_watch_rows(payload)

    assert payload["strong"]
    assert all(item["metadata_source"] not in {"demo_seed", "synthetic_seed"} for item in payload["strong"])

    fallback_rows = [row for row in rows if row["metadata_source"] in {"demo_seed", "synthetic_seed"}]
    assert fallback_rows
    assert all(row["data_origin"] == "fallback" for row in fallback_rows)
    assert all(row["operability_status"] != "operable" for row in fallback_rows)


def test_case_d_stale_freshness_degrades_current_state(isolated_scanner_repo) -> None:
    repo = isolated_scanner_repo
    now = datetime.now(UTC)

    seed_stale_data(repo, now)
    payload = watchlist_today_payload()

    assert payload["current_session"] is not None
    assert payload["current_session"]["freshness"] == "vencido"
    assert payload["current_session"]["degraded"] is True
    assert payload["latest_valid_available"] is False
