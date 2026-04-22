from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "meme_research.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore SQLite database from backup file")
    parser.add_argument("backup_file", help="Path to .db backup")
    args = parser.parse_args()

    backup = Path(args.backup_file).expanduser().resolve()
    if not backup.exists():
        print(f"Backup file not found: {backup}")
        return 1

    shutil.copy2(backup, DB_PATH)
    print(f"restored={backup} -> {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
