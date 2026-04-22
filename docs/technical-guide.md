# Technical Guide (Local-Only)

## Runtime model
- One process serves API + dashboard.
- Default DB is SQLite file: `meme_research.db`.
- No required Docker / cloud / auth / multi-user setup.

## Core local endpoints used by dashboard
- `/health`
- `/signals/latest`
- `/signals/top`
- `/outcomes/latest`
- `/metrics/live`
- `/metrics/reports/latest`
- `/market/context`
- `/quality/summary`

## UI state model
- `Operativo`: backend reachable and consistent.
- `Degradado`: backend reachable but freshness/coverage reduced.
- `Sin conexión`: backend request failure.
- `Cargando`: refresh in progress.

## Data scenario controls
- `python scripts/ops.py scenario full`
- `python scripts/ops.py scenario partial`
- `python scripts/ops.py scenario empty`

## Personal maintenance
- Probe quickly:
  - `python scripts/ops.py probe --base-url http://127.0.0.1:8000`
- Capture evidence:
  - `python scripts/ops.py capture --base-url http://127.0.0.1:8000`
- Full demo reset:
  - `python scripts/ops.py demo-ready --base-url http://127.0.0.1:8000`
- Backup DB:
  - `python scripts/ops.py backup-db`
- Restore DB:
  - `python scripts/ops.py restore-db backups/<file>.db`

## Optional/secondary capabilities kept
- PostgreSQL path remains available but optional.
- Docker compose remains optional.
# Technical Guide

## What This Project Does
This project is a Solana-first meme research and scoring system with a FastAPI backend and a built-in dashboard UI.

Core capabilities:
- Discovery and scoring for meme tokens (long/short setups).
- Deterministic risk gates plus confidence and reasons.
- Runtime market context endpoint (`/market/context`).
- Runtime data quality endpoint (`/quality/summary`).
- Outcome tracking and performance metrics.
- Dashboard with coherent operational/degraded/offline states.

## Architecture Overview
- `app/main.py`: FastAPI app bootstrap, static mount (`/static`), router wiring, scheduler lifecycle.
- `app/clients`: External API adapters (DexScreener, Birdeye, GoPlus, Honeypot, Helius, CoinGlass, Telegram).
- `app/ingestion`: Discovery + market/security/wallet flow feature providers.
- `app/features`: TA features and normalization.
- `app/scoring`: Risk gating, score model, decision engine, explainability.
- `app/storage`: SQLAlchemy models + repositories.
- `app/jobs`: Scan, outcomes, metrics background jobs.
- `app/services`: Release V3 service layer (`market_context_service`, `data_quality_service`).
- `app/api`: HTTP routes for dashboard and APIs.
- `app/web`: Dashboard HTML/CSS/JS (served by backend).

## Main Endpoints
- `GET /`: Dashboard UI
- `GET /health`
- `GET /signals/latest?limit=...`
- `GET /signals/top?decision=LONG_SETUP|SHORT_SETUP&limit=...`
- `GET /tokens/{address}/explain`
- `GET /tokens/{address}/history?limit=...`
- `GET /outcomes/latest?limit=...`
- `GET /metrics/live?horizon=4h`
- `GET /metrics/reports/latest?limit=...`
- `GET /market/context`
- `GET /quality/summary`
- `POST /jobs/run-scan`

## Dashboard Data Flow
1. Browser loads `/` and `/static/dashboard.js`.
2. `dashboard.js` requests these backend APIs in parallel:
   - `/health`
   - `/signals/latest?limit=200`
   - `/signals/top?...`
   - `/outcomes/latest?...`
   - `/metrics/live?horizon=4h`
   - `/metrics/reports/latest?...`
   - `/market/context`
   - `/quality/summary`
3. UI composes:
   - executive summary,
   - market context,
   - quality card,
   - system/performance KPIs,
   - signal tables,
   - charts and token detail drawer.
4. If any critical request fails, UI switches to explicit offline fallback state.

## UI Global States
- `Operativo`: backend reachable, datasets coherent.
- `Degradado`: backend reachable but partial/older/insufficient data quality.
- `Sin conexión`: request failures to backend; panel enters safe fallback.

## Market Context Calculation
Implemented in `app/services/market_context_service.py`.

Inputs:
- DexScreener search results for:
  - `BTC USDC`
  - `SOL USDC`
  - `solana meme`

Derived fields:
- `btc_trend`: average `priceChange.h24` thresholded to `alcista|neutral|bajista`.
- `sol_trend`: same method for SOL universe.
- `meme_regime`: derived from average meme universe change.
- `market_liquidity`: bucket from summed meme-pair liquidity.
- `confidence`: bounded confidence by available data sources.
- `status`, `degraded_reasons`, `stale_sources` for observability.

## Quality Summary Behavior
Implemented in `app/services/data_quality_service.py`.

Data source:
- Latest timestamps and counts from `SignalRepository`.

Per-dataset outputs:
- `signals`, `outcomes`, `metrics` each with:
  - `count`
  - `freshness` (`fresco|degradado|vencido|sin datos`)
  - `minutes_ago`
  - `last_update`

Aggregate outputs:
- `status`: `ok|degradado`
- `degraded_reasons`
- `calculated_at`

## QA and Testing
### Unit / logic tests
- `pytest -q`

### Dashboard E2E (Playwright)
- Install browsers once:
  - `python -m playwright install chromium`
- Run full suite:
  - `python -m pytest tests/e2e/test_dashboard_e2e.py -q`

### Runtime probe
- `python scripts/probe_api.py --base-url http://127.0.0.1:8000 --fail-on-error`

### Evidence capture
- `python scripts/capture_dashboard_evidence.py --base-url http://127.0.0.1:8000`

## Scenario Simulation
### Backend OK (demo data)
- `python scripts/set_qa_scenario.py full`

### Degraded data
- `python scripts/set_qa_scenario.py partial`

### No data
- `python scripts/set_qa_scenario.py empty`

### Backend down
- Stop uvicorn process and refresh dashboard.
- Expected: global `Sin conexión`, explicit offline banner, safe fallback values.

## Operations CLI
`python scripts/ops.py` provides a single operator-facing entrypoint.

Useful commands:
- `python scripts/ops.py serve-sqlite --host 127.0.0.1 --port 8000`
- `python scripts/ops.py serve-postgres --host 127.0.0.1 --port 8000`
- `python scripts/ops.py scenario full`
- `python scripts/ops.py probe --base-url http://127.0.0.1:8000`
- `python scripts/ops.py e2e --base-url http://127.0.0.1:8000`
- `python scripts/ops.py demo-ready --base-url http://127.0.0.1:8000`
