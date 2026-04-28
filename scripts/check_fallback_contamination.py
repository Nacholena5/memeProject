#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


MAIN_BLOCKS = {"LONG ahora", "WATCHLIST prioritaria"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detecta tokens fallback/demo/synthetic en bloques principales.")
    parser.add_argument("--database-url", default=None, help="Sobrescribe DATABASE_URL (ej: sqlite:///./meme_research.db)")
    parser.add_argument("--fail-on-detection", action="store_true", help="Retorna exit code 1 si hay contaminación")
    return parser.parse_args()


def _is_fallback_like(row: object) -> bool:
    source = str(getattr(row, "metadata_source", "") or "").lower()
    confidence = str(getattr(row, "metadata_confidence", "") or "").lower()
    return bool(
        getattr(row, "metadata_is_fallback", False)
        or confidence in {"fallback", "unverified"}
        or source in {"local_fallback", "demo_seed", "synthetic_seed"}
    )


def main() -> int:
    args = parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.storage.db import init_db
    from app.storage.repositories.scanner_repository import ScannerRepository

    init_db()
    repo = ScannerRepository()
    rows = repo.watchlist_for_day(date.today())

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
        if row.category in MAIN_BLOCKS and _is_fallback_like(row)
    ]

    payload = {
        "date": date.today().isoformat(),
        "main_blocks": sorted(MAIN_BLOCKS),
        "rows_today": len(rows),
        "contamination_count": len(contaminated),
        "contamination_rows": contaminated,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.fail_on_detection and contaminated:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
