#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita contaminación por origen de datos en watchlist diaria.")
    parser.add_argument("--database-url", default=None, help="Sobrescribe DATABASE_URL (ej: sqlite:///./meme_research.db)")
    parser.add_argument("--fail-on-contamination", action="store_true", help="Retorna exit code 1 si detecta contaminación")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.storage.repositories.scanner_repository import ScannerRepository

    repo = ScannerRepository()
    rows = repo.watchlist_for_day(date.today())

    origin_counts: Counter[str] = Counter()
    contamination_rows: list[dict] = []

    for row in rows:
        source = str(row.metadata_source or "").lower()
        confidence = str(row.metadata_confidence or "").lower()

        if source == "demo_seed":
            origin = "demo"
        elif source == "synthetic_seed":
            origin = "synthetic"
        elif row.metadata_is_fallback or confidence in {"fallback", "unverified"}:
            origin = "fallback_stale"
        else:
            origin = "live"

        origin_counts[origin] += 1

        if row.category == "LONG ahora" and origin != "live":
            contamination_rows.append(
                {
                    "token_address": row.token_address,
                    "symbol": row.symbol,
                    "category": row.category,
                    "metadata_source": row.metadata_source,
                    "metadata_confidence": row.metadata_confidence,
                }
            )

    payload = {
        "date": date.today().isoformat(),
        "watchlist_rows": len(rows),
        "origins": dict(origin_counts),
        "contamination_count": len(contamination_rows),
        "contamination_rows": contamination_rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.fail_on_contamination and contamination_rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
