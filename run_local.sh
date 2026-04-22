#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f ".venv/Scripts/python.exe" && ! -f ".venv/bin/python" ]]; then
  echo "No virtual environment found at .venv"
  exit 1
fi

if [[ ! -f ".env.local" && -f ".env.local.example" ]]; then
  cp .env.local.example .env.local
  echo "Created .env.local from template"
fi

PYTHON_BIN=".venv/bin/python"
if [[ -f ".venv/Scripts/python.exe" ]]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
fi

export DATABASE_URL="sqlite:///./meme_research.db"

"$PYTHON_BIN" scripts/ops.py scenario full

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
fi

"$PYTHON_BIN" scripts/ops.py serve-sqlite --host 127.0.0.1 --port 8000
