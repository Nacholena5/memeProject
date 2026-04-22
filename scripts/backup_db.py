from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "meme_research.db"
BACKUP_DIR = ROOT / "backups"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create timestamped SQLite backup")
    parser.add_argument("--name", default="", help="Optional suffix name")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{args.name}" if args.name else ""
    target = BACKUP_DIR / f"meme_research_{ts}{suffix}.db"
    shutil.copy2(DB_PATH, target)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
