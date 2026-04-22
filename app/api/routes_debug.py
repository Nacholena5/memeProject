from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter

from app.services.playbook_scanner_service import scanner_service

router = APIRouter(prefix="/debug", tags=["debug/internal"])


def _is_fallback_like(row: object) -> bool:
    confidence = str(getattr(row, "metadata_confidence", "") or "").lower()
    source = str(getattr(row, "metadata_source", "") or "").lower()
    return bool(
        getattr(row, "metadata_is_fallback", False)
        or confidence in {"fallback", "unverified"}
        or source in {"demo_seed", "synthetic_seed", "local_fallback"}
    )


def _freshness(session: object | None) -> dict:
    if session is None:
        return {"freshness": "none", "minutes_ago": None}
    if session.finished_at is None:
        return {"freshness": "running", "minutes_ago": 0.0}
    finished_at = session.finished_at
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=UTC)
    minutes = max(0.0, (datetime.now(UTC) - finished_at).total_seconds() / 60.0)
    if minutes <= 60:
        label = "fresco"
    elif minutes <= 180:
        label = "degradado"
    else:
        label = "vencido"
    return {"freshness": label, "minutes_ago": round(minutes, 1)}


@router.get("/data-origins")
def debug_data_origins() -> dict:
    rows = scanner_service.repo.watchlist_for_day(date.today())
    origins = {
        "live": 0,
        "historical": 0,
        "demo": 0,
        "synthetic": 0,
        "fallback_stale": 0,
    }
    contamination = []

    for row in rows:
        source = str(row.metadata_source or "").lower()
        if source == "demo_seed":
            origin = "demo"
        elif source == "synthetic_seed":
            origin = "synthetic"
        elif _is_fallback_like(row):
            origin = "fallback_stale"
        else:
            origin = "live"
        origins[origin] += 1

        if row.category == "LONG ahora" and origin in {"demo", "synthetic", "fallback_stale"}:
            contamination.append(
                {
                    "token_address": row.token_address,
                    "symbol": row.symbol,
                    "category": row.category,
                    "metadata_source": row.metadata_source,
                    "metadata_confidence": row.metadata_confidence,
                }
            )

    return {
        "internal": True,
        "date": date.today().isoformat(),
        "total_rows": len(rows),
        "origins": origins,
        "contamination_detected": bool(contamination),
        "contamination_rows": contamination,
    }


@router.get("/session-health")
def debug_session_health() -> dict:
    current = scanner_service.repo.latest_session()
    latest_valid = scanner_service.repo.latest_valid_session()

    current_fresh = _freshness(current)
    valid_fresh = _freshness(latest_valid)

    return {
        "internal": True,
        "current": {
            "scan_session_id": current.id if current else None,
            "status": current.status if current else None,
            "degraded": current.degraded if current else None,
            **current_fresh,
        },
        "latest_valid": {
            "scan_session_id": latest_valid.id if latest_valid else None,
            "status": latest_valid.status if latest_valid else None,
            "degraded": latest_valid.degraded if latest_valid else None,
            **valid_fresh,
        },
    }


@router.get("/current-vs-valid")
def debug_current_vs_valid() -> dict:
    current = scanner_service.repo.latest_session()
    latest_valid = scanner_service.repo.latest_valid_session()

    selected_source = "none"
    selected_session_id = None

    if current and current.status == "completed" and not current.degraded and current.watchlist_count > 0:
        selected_source = "current"
        selected_session_id = current.id
    elif latest_valid is not None:
        selected_source = "latest_valid"
        selected_session_id = latest_valid.id
    elif current is not None:
        selected_source = "current"
        selected_session_id = current.id

    return {
        "internal": True,
        "selected_source": selected_source,
        "selected_session_id": selected_session_id,
        "current_session_id": current.id if current else None,
        "latest_valid_session_id": latest_valid.id if latest_valid else None,
    }


@router.get("/fallback-contamination")
def debug_fallback_contamination() -> dict:
    rows = scanner_service.repo.watchlist_for_day(date.today())
    main_blocks = {"LONG ahora", "WATCHLIST prioritaria"}

    contaminated = [
        {
            "token_address": row.token_address,
            "symbol": row.symbol,
            "category": row.category,
            "metadata_source": row.metadata_source,
            "metadata_confidence": row.metadata_confidence,
            "metadata_is_fallback": row.metadata_is_fallback,
        }
        for row in rows
        if row.category in main_blocks and _is_fallback_like(row)
    ]

    return {
        "internal": True,
        "date": date.today().isoformat(),
        "main_blocks": sorted(main_blocks),
        "total_rows": len(rows),
        "contamination_count": len(contaminated),
        "contamination_rows": contaminated,
    }
