from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services import playbook_scanner_service as service


def _mk_row(
    *,
    metadata_confidence: str = "confirmed",
    metadata_is_fallback: bool = False,
    category: str = "LONG ahora",
    risk_label: str = "bajo",
    liquidity_usd: float = 200_000.0,
    payload_json: dict | None = None,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        token_address="So11111111111111111111111111111111111111112",
        symbol="SOL",
        category=category,
        score_long=80.0,
        score_short=20.0,
        confidence=0.9,
        risk_label=risk_label,
        risk_value=12.0,
        liquidity_usd=liquidity_usd,
        metadata_source="dexscreener",
        metadata_confidence=metadata_confidence,
        metadata_is_fallback=metadata_is_fallback,
        metadata_last_source="dexscreener",
        metadata_last_validated_at=now,
        metadata_conflict=False,
        rank_order=1,
        main_reason="ok",
        explanation="ok",
        payload_json=payload_json or {"signal_dimensions": {"composite": {}}},
        created_at=now,
        scan_session_id=1,
    )


def _mk_session(
    session_id: int,
    *,
    status: str = "completed",
    degraded: bool = False,
    watchlist_count: int = 1,
    minutes_ago: int = 15,
    trigger: str = "manual",
) -> SimpleNamespace:
    finished_at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return SimpleNamespace(
        id=session_id,
        started_at=finished_at - timedelta(minutes=5),
        finished_at=finished_at,
        status=status,
        degraded=degraded,
        watchlist_count=watchlist_count,
        discarded_count=0,
        source_summary_json={},
        notes_json={},
        config_json={"trigger": trigger},
    )


def test_watch_row_marks_fallback_not_primary_eligible() -> None:
    row = _mk_row(metadata_confidence="fallback", metadata_is_fallback=True)
    payload = service._watch_row(
        row,
        source_type="current",
        freshness_state="fresco",
        session_timestamp=datetime.now(UTC).isoformat(),
        is_demo=False,
        min_primary_liquidity=150_000.0,
    )
    assert payload["data_origin"] == "fallback"
    assert payload["fallback_only"] is True
    assert payload["is_primary_eligible"] is False


def test_watch_row_live_confirmed_can_be_primary_eligible() -> None:
    row = _mk_row(metadata_confidence="confirmed", metadata_is_fallback=False, risk_label="bajo", liquidity_usd=250_000.0)
    payload = service._watch_row(
        row,
        source_type="current",
        freshness_state="fresco",
        session_timestamp=datetime.now(UTC).isoformat(),
        is_demo=False,
        min_primary_liquidity=150_000.0,
    )
    assert payload["data_origin"] == "live"
    assert payload["is_primary_eligible"] is True
    assert payload["is_current_session"] is True


def test_watchlist_payload_uses_latest_valid_when_current_invalid(monkeypatch) -> None:
    current = _mk_session(100, degraded=True, watchlist_count=0)
    latest_valid = _mk_session(99, degraded=False, watchlist_count=2)
    watch_rows = [_mk_row()]

    class FakeRepo:
        def latest_session(self):
            return current

        def latest_valid_session(self):
            return latest_valid

        def watchlist_for_session(self, session_id: int):
            return watch_rows if session_id == latest_valid.id else []

        def discarded_for_session(self, _session_id: int):
            return []

        def discarded_for_day(self, _today):
            return []

        def latest_session_with_watchlist(self):
            return latest_valid

    settings = SimpleNamespace(
        scanner_watchlist_strong_limit=10,
        scanner_watchlist_observe_limit=10,
        scanner_watchlist_short_limit=10,
        scanner_min_liquidity_usd=150_000.0,
    )

    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service.scanner_service, "repo", FakeRepo())

    payload = service.watchlist_today_payload()

    assert payload["source"] == "latest_valid"
    assert payload["is_current_session"] is False
    assert payload["is_latest_valid_session"] is True
    assert payload["is_historical_only"] is True
    assert payload["session_type"] == "latest_valid_session"
    assert payload["total"] == 1

