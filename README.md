# Meme Research Local Dashboard

Personal local-only trading intelligence dashboard for meme-coin research.

This repo is optimized for one user, one machine, SQLite-first usage.

## What it does
- Runs a FastAPI backend + dashboard UI in one local process.
- Shows V3 dashboard with:
  - system summary,
  - market context (`/market/context`),
  - data quality (`/quality/summary`),
  - top signals tables,
  - detail drawer,
  - local charts and robust fallback states.

## Local-first setup (recommended)
1. Create and activate venv.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Prepare local env file:
   - `copy .env.local.example .env.local`
4. Start app:
   - `run_local.ps1`
5. Open browser:
   - `http://127.0.0.1:8000`

Notes:
- SQLite is the default path (`sqlite:///./meme_research.db`).
- `.env.local` is loaded before `.env`.

## Daily commands (short)
- Start local server (SQLite):
  - `python scripts/ops.py serve-sqlite --host 127.0.0.1 --port 8000`
- Reset demo state:
  - `python scripts/ops.py reset-demo`
- Apply QA scenario:
  - `python scripts/ops.py scenario full`
  - `python scripts/ops.py scenario partial`
  - `python scripts/ops.py scenario empty`
- Probe backend quickly:
  - `python scripts/ops.py probe --base-url http://127.0.0.1:8000`
- Run scanner playbook now:
  - `python scripts/ops.py scanner-run --base-url http://127.0.0.1:8000`
- Inspect scanner watchlist API:
  - `http://127.0.0.1:8000/scanner/watchlist/today`
- Inspect scanner discarded API:
  - `http://127.0.0.1:8000/scanner/discarded/today`
- Capture dashboard evidence (png + json):
  - `python scripts/ops.py capture --base-url http://127.0.0.1:8000`
- End-to-end tests:
  - `python scripts/ops.py e2e --base-url http://127.0.0.1:8000`

## Data integrity guardrails (live/historical/demo/synthetic/fallback/stale)
- Automated tests (isolated SQLite, no DB contamination required):
  - `python -m pytest tests/test_data_integrity_guardrails.py`
- Audit data origins and contamination in main blocks:
  - `python scripts/check_data_origins.py --fail-on-contamination`
- Compare current session vs latest valid session and stale usage:
  - `python scripts/check_session_integrity.py --strict`
- Detect fallback/demo/synthetic rows in principal blocks:
  - `python scripts/check_fallback_contamination.py --fail-on-detection`

Optional debug/internal endpoints:
- `GET /debug/data-origins`
- `GET /debug/session-health`
- `GET /debug/current-vs-valid`
- `GET /debug/fallback-contamination`

Quick dashboard honesty check:
1. Run `python scripts/check_data_origins.py --fail-on-contamination`
2. Run `python scripts/check_session_integrity.py --strict`
3. Verify `/scanner/watchlist/today` shows no `LONG ahora` with fallback/demo/synthetic metadata

## Backup / restore local DB
- Create backup:
  - `python scripts/ops.py backup-db`
- Create named backup:
  - `python scripts/ops.py backup-db --name before_big_change`
- Restore backup:
  - `python scripts/ops.py restore-db backups/<file>.db`

## If something breaks
1. Stop server process.
2. Run:
   - `python scripts/ops.py reset-demo`
3. Run:
   - `python scripts/ops.py probe --base-url http://127.0.0.1:8000`
4. Start again:
   - `run_local.ps1`

## Important files
- `app/main.py`: app entrypoint.
- `app/web/static/dashboard.js`: dashboard runtime logic.
- `app/services/market_context_service.py`: market context logic.
- `app/services/data_quality_service.py`: data quality logic.
- `scripts/ops.py`: local operator CLI.
- `.env.local.example`: personal local env template.

## Optional PostgreSQL path (secondary)
Not needed for normal local usage.
- `docker compose up -d`
- `python scripts/ops.py serve-postgres --host 127.0.0.1 --port 8000`

## More docs
- `docs/technical-guide.md`
- `docs/demo-checklist.md`
- `docs/handoff.md`
