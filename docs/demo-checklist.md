# Demo Checklist (Local Personal)

## 1. Boot Everything
1. Start locally with one command: `run_local.ps1`
2. If needed, reset data: `python scripts/ops.py reset-demo`

## 2. Verify It Is Healthy
1. Probe APIs: `python scripts/ops.py probe --base-url http://127.0.0.1:8000`
2. Open dashboard: `http://127.0.0.1:8000`
3. Confirm offline banner is hidden.

## 3. Demo Sequence
1. Show global status badge and explain state meaning.
2. Show `Resumen del sistema` (bias, risk, best opportunities).
3. Show `Contexto de mercado` (BTC/SOL/regime/liquidity).
4. Show `Calidad de datos` (freshness + coverage).
5. Show top long/short tables and reasons.
6. Click `Ver detalle` on one signal and explain drawer.
7. Show outcomes and quality-history charts.

## 4. Resilience Moment (Backend Failure)
1. Stop server process.
2. Refresh dashboard.
3. Show explicit `Sin conexión` banner + safe fallback state.

## 5. Return to Demo-Ready
1. Restart API with sqlite fallback.
2. Run: `python scripts/ops.py demo-ready --base-url http://127.0.0.1:8000`
3. Reload dashboard and continue demo.
