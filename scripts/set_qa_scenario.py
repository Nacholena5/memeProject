from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.seed_demo_data import seed

DB_PATH = Path("meme_research.db")


def _exec(sql: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def clear_all() -> None:
    _exec(
        """
        DELETE FROM signal_outcomes;
        DELETE FROM performance_reports;
        DELETE FROM score_snapshots;
        """
    )


def scenario_full() -> None:
    clear_all()
    seed()


def scenario_partial() -> None:
    clear_all()
    seed()
    _exec(
        """
        DELETE FROM performance_reports;
        DELETE FROM signal_outcomes;
        UPDATE score_snapshots SET reasons_json = '{}' WHERE id % 3 = 0;
        """
    )


def scenario_empty() -> None:
    clear_all()


def main(mode: str) -> None:
    if mode == "full":
        scenario_full()
    elif mode == "partial":
        scenario_partial()
    elif mode == "empty":
        scenario_empty()
    else:
        raise SystemExit(f"Unknown mode: {mode}")

    print(f"Scenario applied: {mode}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: set_qa_scenario.py [full|partial|empty]")
    main(sys.argv[1])
