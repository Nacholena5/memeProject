#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, date, datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compara sesión current vs latest valid y detecta stale como actual.")
    parser.add_argument("--database-url", default=None, help="Sobrescribe DATABASE_URL (ej: sqlite:///./meme_research.db)")
    parser.add_argument("--strict", action="store_true", help="Retorna exit code 1 cuando current está stale/degradada")
    return parser.parse_args()


def _freshness(session) -> dict:
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


def main() -> int:
    args = parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.storage.repositories.scanner_repository import ScannerRepository

    repo = ScannerRepository()
    current = repo.latest_session()
    latest_valid = repo.latest_valid_session()

    today_rows = repo.watchlist_for_day(date.today())
    current_today = repo.session_by_id(today_rows[0].scan_session_id) if today_rows else None

    current_freshness = _freshness(current_today)
    stale_current = bool(current_today and current_freshness["freshness"] in {"degradado", "vencido"})

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

    payload = {
        "current_session": {
            "scan_session_id": current.id if current else None,
            "status": current.status if current else None,
            "degraded": current.degraded if current else None,
        },
        "current_session_from_today": {
            "scan_session_id": current_today.id if current_today else None,
            "status": current_today.status if current_today else None,
            "degraded": current_today.degraded if current_today else None,
            **current_freshness,
        },
        "latest_valid_session": {
            "scan_session_id": latest_valid.id if latest_valid else None,
            "status": latest_valid.status if latest_valid else None,
            "degraded": latest_valid.degraded if latest_valid else None,
            **_freshness(latest_valid),
        },
        "selection": {
            "selected_source": selected_source,
            "selected_session_id": selected_session_id,
        },
        "stale_current_used_as_actual": stale_current,
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.strict and stale_current:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
