from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class MetadataSeed:
    source: str
    confidence: str
    is_fallback: bool
    validated_at: datetime | None
    conflict: bool = False


def metadata_live_valid(now: datetime) -> MetadataSeed:
    return MetadataSeed(
        source="dexscreener",
        confidence="confirmed",
        is_fallback=False,
        validated_at=now - timedelta(minutes=15),
    )


def metadata_historical(now: datetime) -> MetadataSeed:
    return MetadataSeed(
        source="dexscreener",
        confidence="inferred",
        is_fallback=False,
        validated_at=now - timedelta(hours=6),
    )


def metadata_demo(now: datetime) -> MetadataSeed:
    return MetadataSeed(
        source="demo_seed",
        confidence="fallback",
        is_fallback=True,
        validated_at=now - timedelta(minutes=20),
    )


def metadata_synthetic(now: datetime) -> MetadataSeed:
    return MetadataSeed(
        source="synthetic_seed",
        confidence="fallback",
        is_fallback=True,
        validated_at=now - timedelta(minutes=30),
    )


def metadata_fallback_identity(now: datetime) -> MetadataSeed:
    return MetadataSeed(
        source="local_fallback",
        confidence="fallback",
        is_fallback=True,
        validated_at=now - timedelta(minutes=10),
    )


def metadata_stale(now: datetime) -> MetadataSeed:
    return MetadataSeed(
        source="dexscreener",
        confidence="confirmed",
        is_fallback=False,
        validated_at=now - timedelta(days=2),
    )


def _watch_row(session_id: int, created_at: datetime, token: str, symbol: str, category: str, meta: MetadataSeed) -> dict:
    return {
        "scan_session_id": session_id,
        "token_address": token,
        "symbol": symbol,
        "category": category,
        "score_long": 74.0,
        "score_short": 41.0,
        "confidence": 0.79,
        "risk_label": "medio",
        "risk_value": 24.0,
        "liquidity_usd": 180_000.0,
        "rank_order": 1,
        "main_reason": "Candidato de prueba",
        "explanation": "Seed de integridad",
        "metadata_source": meta.source,
        "metadata_confidence": meta.confidence,
        "metadata_is_fallback": meta.is_fallback,
        "metadata_last_source": meta.source,
        "metadata_last_validated_at": meta.validated_at,
        "metadata_conflict": meta.conflict,
        "payload_json": {},
        "created_at": created_at,
    }


def _discard_row(session_id: int, created_at: datetime, token: str, symbol: str, reason: str, meta: MetadataSeed) -> dict:
    return {
        "scan_session_id": session_id,
        "token_address": token,
        "symbol": symbol,
        "category": "NO TRADE",
        "discard_reason": reason,
        "metadata_source": meta.source,
        "metadata_confidence": meta.confidence,
        "metadata_is_fallback": meta.is_fallback,
        "metadata_last_source": meta.source,
        "metadata_last_validated_at": meta.validated_at,
        "metadata_conflict": meta.conflict,
        "flags_json": {"seed": True},
        "created_at": created_at,
    }


def create_completed_session(_repo, *, started_at: datetime, finished_at: datetime, degraded: bool, watchlist_count: int, discarded_count: int, notes: dict | None = None) -> int:
    """Create a completed ScanSession row directly. The _repo arg is accepted for call-site readability but is unused."""
    from app.storage.db import ScanSession, get_session

    with get_session() as session:
        row = ScanSession(
            started_at=started_at,
            finished_at=finished_at,
            status="completed",
            degraded=degraded,
            source_summary_json={"seed": "ok"},
            config_json={"seed": True},
            discovered_count=watchlist_count + discarded_count,
            validated_count=watchlist_count + discarded_count,
            classified_count=watchlist_count + discarded_count,
            watchlist_count=watchlist_count,
            discarded_count=discarded_count,
            notes_json=notes or {},
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def seed_live_data_valid(repo, now: datetime) -> int:
    session_id = create_completed_session(
        repo,
        started_at=now - timedelta(minutes=25),
        finished_at=now - timedelta(minutes=5),
        degraded=False,
        watchlist_count=1,
        discarded_count=0,
        notes={"seed_type": "live"},
    )
    repo.add_watchlist_entries([
        _watch_row(session_id, now - timedelta(minutes=4), "live-addr-1", "LIVE", "LONG ahora", metadata_live_valid(now))
    ])
    return session_id


def seed_historical_data(repo, now: datetime) -> int:
    historical_time = now - timedelta(days=1, hours=1)
    session_id = create_completed_session(
        repo,
        started_at=historical_time - timedelta(minutes=30),
        finished_at=historical_time,
        degraded=False,
        watchlist_count=1,
        discarded_count=0,
        notes={"seed_type": "historical"},
    )
    repo.add_watchlist_entries([
        _watch_row(session_id, historical_time, "hist-addr-1", "HIST", "LONG ahora", metadata_historical(now))
    ])
    return session_id


def seed_demo_data(repo, now: datetime) -> int:
    session_id = create_completed_session(
        repo,
        started_at=now - timedelta(minutes=40),
        finished_at=now - timedelta(minutes=30),
        degraded=False,
        watchlist_count=1,
        discarded_count=0,
        notes={"seed_type": "demo"},
    )
    repo.add_watchlist_entries([
        _watch_row(session_id, now - timedelta(minutes=29), "demo-addr-1", "DEMO", "WATCHLIST prioritaria", metadata_demo(now))
    ])
    return session_id


def seed_synthetic_data(repo, now: datetime) -> int:
    session_id = create_completed_session(
        repo,
        started_at=now - timedelta(minutes=35),
        finished_at=now - timedelta(minutes=20),
        degraded=False,
        watchlist_count=1,
        discarded_count=0,
        notes={"seed_type": "synthetic"},
    )
    repo.add_watchlist_entries([
        _watch_row(session_id, now - timedelta(minutes=19), "synthetic-addr-1", "SYN", "WATCHLIST secundaria", metadata_synthetic(now))
    ])
    return session_id


def seed_fallback_identities(repo, now: datetime) -> int:
    session_id = create_completed_session(
        repo,
        started_at=now - timedelta(minutes=20),
        finished_at=now - timedelta(minutes=8),
        degraded=False,
        watchlist_count=1,
        discarded_count=1,
        notes={"seed_type": "fallback"},
    )
    fallback_meta = metadata_fallback_identity(now)
    repo.add_watchlist_entries([
        _watch_row(session_id, now - timedelta(minutes=7), "fallback-addr-1", "FBK", "WATCHLIST secundaria", fallback_meta)
    ])
    repo.add_discarded_entries([
        _discard_row(session_id, now - timedelta(minutes=6), "fallback-addr-2", "FB2", "fallback identity bloqueada", fallback_meta)
    ])
    return session_id


def seed_stale_data(repo, now: datetime) -> int:
    stale_finished = now - timedelta(hours=5)
    session_id = create_completed_session(
        repo,
        started_at=stale_finished - timedelta(minutes=25),
        finished_at=stale_finished,
        degraded=True,
        watchlist_count=1,
        discarded_count=0,
        notes={"seed_type": "stale"},
    )
    repo.add_watchlist_entries([
        _watch_row(session_id, now - timedelta(minutes=1), "stale-addr-1", "STL", "WATCHLIST prioritaria", metadata_stale(now))
    ])
    return session_id


@pytest.fixture
def isolated_scanner_repo(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from app.storage import db as storage_db
    from app.storage.repositories.scanner_repository import ScannerRepository
    import app.services.playbook_scanner_service as scanner_module
    import app.api.routes_scanner as scanner_routes

    db_path = tmp_path / "integrity_tests.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True, pool_pre_ping=True)
    session_local = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    monkeypatch.setattr(storage_db, "engine", engine)
    monkeypatch.setattr(storage_db, "SessionLocal", session_local)
    storage_db.Base.metadata.create_all(bind=engine)

    repo = ScannerRepository()
    test_service = SimpleNamespace(repo=repo)
    monkeypatch.setattr(scanner_module, "scanner_service", test_service)
    monkeypatch.setattr(scanner_routes, "scanner_service", test_service)

    return repo
