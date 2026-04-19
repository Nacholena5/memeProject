from fastapi import APIRouter, Query

from app.analytics.metrics_service import MetricsService
from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/metrics", tags=["metrics"])
repo = SignalRepository()
service = MetricsService(repo)


@router.get("/reports/latest")
def latest_reports(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    rows = repo.latest_performance_reports(limit=limit)
    return [
        {
            "ts": row.ts.isoformat(),
            "horizon": row.horizon,
            "n_signals": row.n_signals,
            "win_rate": row.win_rate,
            "avg_win": row.avg_win,
            "avg_loss": row.avg_loss,
            "expectancy": row.expectancy,
            "precision_top_decile": row.precision_top_decile,
            "max_drawdown_proxy": row.max_drawdown_proxy,
            "sharpe_proxy": row.sharpe_proxy,
        }
        for row in rows
    ]


@router.get("/live")
def live(horizon: str = Query(default="4h")) -> dict:
    snap = service.compute_for_horizon(horizon=horizon, min_rows=10)
    if snap is None:
        return {"horizon": horizon, "status": "insufficient_data"}

    return {
        "horizon": snap.horizon,
        "n_signals": snap.n_signals,
        "win_rate": snap.win_rate,
        "avg_win": snap.avg_win,
        "avg_loss": snap.avg_loss,
        "expectancy": snap.expectancy,
        "precision_top_decile": snap.precision_top_decile,
        "max_drawdown_proxy": snap.max_drawdown_proxy,
        "sharpe_proxy": snap.sharpe_proxy,
    }
