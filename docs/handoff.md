# Technical Handoff (Local-Only)

## Completed Scope
- Backend V3 endpoints integrated and in use:
  - `/market/context`
  - `/quality/summary`
- Dashboard V3 wired to backend endpoints.
- Local chart dependency vendored (`app/web/static/vendor/chart.umd.min.js`), no runtime CDN dependency.
- E2E dashboard suite implemented (`tests/e2e/test_dashboard_e2e.py`).
- Runtime discrepancy (old backend/new frontend mismatch) resolved by enforcing correct runtime instance.
- Local operations CLI added (`scripts/ops.py`) with scenario, probe, capture, backup and restore.
- Local launchers added (`run_local.ps1`, `run_local.bat`, `run_local.sh`).

## Real Pending Items
- If external provider APIs are down/rate-limited, context/quality can degrade (expected behavior).
- Provider credentials (Birdeye/Helius/etc.) remain environment-dependent for full live data quality in non-demo environments.

## Key Technical Decisions
- Keep backend and dashboard in one local process to avoid version drift.
- Use explicit global UI status states (`Operativo`, `Degradado`, `Sin conexión`) to avoid ambiguous dashboard behavior.
- Expose quality and context as first-class backend APIs rather than frontend-derived heuristics.
- Use local vendored chart asset for deterministic demos without external CDN availability risk.

## Tradeoffs
- SQLite-first design is optimal for single-user local workflows.
- Market context currently relies on DexScreener query-based sampling, which is lightweight but heuristic.
- E2E tests validate UX behavior and contracts, but are still dependent on runtime availability at target base URL.

## Suggested V4 (Only Practical Next Steps)
- Persist context snapshots for trend visualization.
- Add one-click in-app action for DB backup/restore.
- Add optional light caching for external provider responses.
