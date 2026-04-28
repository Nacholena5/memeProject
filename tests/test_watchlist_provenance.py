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
    metadata_source: str = "dexscreener",
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
        metadata_source=metadata_source,
        metadata_confidence=metadata_confidence,
        metadata_is_fallback=metadata_is_fallback,
        metadata_last_source=metadata_source,
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


def _watch_row(row, *, source_type="current", freshness_state="fresco", is_demo=False, min_liq=150_000.0):
    return service._watch_row(
        row,
        source_type=source_type,
        freshness_state=freshness_state,
        session_timestamp=datetime.now(UTC).isoformat(),
        is_demo=is_demo,
        min_primary_liquidity=min_liq,
    )


# ── existing tests ────────────────────────────────────────────────────────────

def test_watch_row_marks_fallback_not_primary_eligible() -> None:
    row = _mk_row(metadata_confidence="fallback", metadata_is_fallback=True)
    payload = _watch_row(row)
    assert payload["data_origin"] == "fallback"
    assert payload["fallback_only"] is True
    assert payload["is_primary_eligible"] is False
    assert "unverified_identity" in payload["primary_blockers"]


def test_watch_row_live_confirmed_can_be_primary_eligible() -> None:
    row = _mk_row(metadata_confidence="confirmed", metadata_is_fallback=False, risk_label="bajo", liquidity_usd=250_000.0)
    payload = _watch_row(row)
    assert payload["data_origin"] == "live"
    assert payload["is_primary_eligible"] is True
    assert payload["is_current_session"] is True
    assert payload["primary_blockers"] == []


# ── individual blocking conditions ───────────────────────────────────────────

def test_stale_freshness_blocks_primary_eligibility() -> None:
    """Sesión vencida bloquea is_primary_eligible aunque todo lo demás sea OK."""
    row = _mk_row(metadata_confidence="confirmed", risk_label="bajo", liquidity_usd=250_000.0)
    payload = _watch_row(row, freshness_state="vencido")
    assert payload["is_primary_eligible"] is False
    assert "stale_session" in payload["primary_blockers"]
    assert payload["data_origin"] == "stale"


def test_demo_session_blocks_primary_eligibility() -> None:
    """Row de sesión demo bloquea is_primary_eligible y marca data_origin='demo'."""
    row = _mk_row(metadata_confidence="confirmed", risk_label="bajo", liquidity_usd=250_000.0)
    payload = _watch_row(row, is_demo=True)
    assert payload["is_demo"] is True
    assert payload["is_primary_eligible"] is False
    assert "demo_or_synthetic" in payload["primary_blockers"]
    assert payload["data_origin"] == "demo"


def test_synthetic_row_blocks_primary_eligibility() -> None:
    """Row marcada como synthetic bloquea is_primary_eligible."""
    row = _mk_row(
        metadata_confidence="confirmed",
        risk_label="bajo",
        liquidity_usd=250_000.0,
        payload_json={"signal_dimensions": {"composite": {}}, "is_synthetic": True},
    )
    payload = _watch_row(row)
    assert payload["is_synthetic"] is True
    assert payload["is_primary_eligible"] is False
    assert "demo_or_synthetic" in payload["primary_blockers"]
    assert payload["data_origin"] == "synthetic"


def test_high_risk_blocks_primary_eligibility() -> None:
    """Riesgo alto bloquea is_primary_eligible."""
    row = _mk_row(metadata_confidence="confirmed", risk_label="alto", liquidity_usd=250_000.0)
    payload = _watch_row(row)
    assert payload["is_primary_eligible"] is False
    assert "risk_not_acceptable" in payload["primary_blockers"]


def test_low_liquidity_blocks_primary_eligibility() -> None:
    """Liquidez baja bloquea is_primary_eligible."""
    row = _mk_row(metadata_confidence="confirmed", risk_label="bajo", liquidity_usd=50_000.0)
    payload = _watch_row(row, min_liq=150_000.0)
    assert payload["is_primary_eligible"] is False
    assert "low_liquidity" in payload["primary_blockers"]


def test_unverified_identity_blocks_primary_eligibility() -> None:
    """Identidad unverified bloquea is_primary_eligible."""
    row = _mk_row(metadata_confidence="unverified", metadata_is_fallback=False)
    payload = _watch_row(row)
    assert payload["is_primary_eligible"] is False
    assert "unverified_identity" in payload["primary_blockers"]


def test_non_operable_category_blocks_primary_eligibility() -> None:
    """Categoría WATCHLIST (no operable) no puede ser is_primary_eligible."""
    row = _mk_row(metadata_confidence="confirmed", risk_label="bajo", liquidity_usd=250_000.0, category="WATCHLIST prioritaria")
    payload = _watch_row(row)
    assert payload["operability_status"] != "operable"
    assert payload["is_primary_eligible"] is False


def test_historical_origin_still_eligible_when_valid() -> None:
    """Sesión latest_valid (histórico reciente) puede ser is_primary_eligible si es válido."""
    row = _mk_row(metadata_confidence="confirmed", risk_label="bajo", liquidity_usd=250_000.0)
    payload = _watch_row(row, source_type="latest_valid", freshness_state="degradado")
    assert payload["data_origin"] == "historical"
    assert payload["is_primary_eligible"] is True


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


def test_watchlist_payload_empty_when_no_sessions(monkeypatch) -> None:
    """Sin sesiones disponibles, el payload es vacío con explicación clara."""

    class EmptyRepo:
        def latest_session(self):
            return None

        def latest_valid_session(self):
            return None

        def watchlist_for_session(self, _session_id: int):
            return []

        def discarded_for_session(self, _session_id: int):
            return []

        def discarded_for_day(self, _today):
            return []

        def latest_session_with_watchlist(self):
            return None

    settings = SimpleNamespace(
        scanner_watchlist_strong_limit=10,
        scanner_watchlist_observe_limit=10,
        scanner_watchlist_short_limit=10,
        scanner_min_liquidity_usd=150_000.0,
    )

    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service.scanner_service, "repo", EmptyRepo())

    payload = service.watchlist_today_payload()

    assert payload["source"] == "none"
    assert payload["total"] == 0
    assert payload["trusted_total"] == 0
    assert payload["empty_explanation"] is not None
    assert payload["is_live"] is False


def test_select_session_prefers_current_when_valid() -> None:
    current = _mk_session(10, status="completed", degraded=False, watchlist_count=3)
    latest_valid = _mk_session(9, status="completed", degraded=False, watchlist_count=2)
    session, scope = service._select_session(current, latest_valid)
    assert scope == "current"
    assert session.id == 10


def test_select_session_falls_back_to_latest_valid() -> None:
    current = _mk_session(10, status="completed", degraded=True, watchlist_count=0)
    latest_valid = _mk_session(9, status="completed", degraded=False, watchlist_count=2)
    session, scope = service._select_session(current, latest_valid)
    assert scope == "latest_valid"
    assert session.id == 9


def test_select_session_returns_none_when_all_empty() -> None:
    session, scope = service._select_session(None, None)
    assert session is None
    assert scope == "none"


def test_is_demo_session_detects_qa_trigger() -> None:
    session = _mk_session(1, trigger="qa_scenario_full")
    assert service._is_demo_session(session) is True


def test_is_demo_session_ignores_manual_trigger() -> None:
    session = _mk_session(1, trigger="manual")
    assert service._is_demo_session(session) is False


def test_acceptable_risk_labels_constant() -> None:
    """Verify the exported constant includes expected labels and excludes 'alto'."""
    assert "bajo" in service._ACCEPTABLE_RISK_LABELS
    assert "medio" in service._ACCEPTABLE_RISK_LABELS
    assert "alto" not in service._ACCEPTABLE_RISK_LABELS

