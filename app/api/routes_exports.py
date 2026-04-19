import csv
import io

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/exports", tags=["exports"])
repo = SignalRepository()


def _to_csv(headers: list[str], rows: list[list]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


@router.get("/outcomes.csv")
def export_outcomes(limit: int = Query(default=500, ge=1, le=5000)) -> PlainTextResponse:
    rows = repo.latest_outcomes(limit=limit)
    csv_text = _to_csv(
        headers=["score_snapshot_id", "horizon", "ret_pct", "max_fav_excursion", "max_adv_excursion"],
        rows=[
            [
                row.score_snapshot_id,
                row.horizon,
                row.ret_pct,
                row.max_fav_excursion,
                row.max_adv_excursion,
            ]
            for row in rows
        ],
    )
    return PlainTextResponse(csv_text, media_type="text/csv")


@router.get("/metrics.csv")
def export_metrics(limit: int = Query(default=500, ge=1, le=5000)) -> PlainTextResponse:
    rows = repo.latest_performance_reports(limit=limit)
    csv_text = _to_csv(
        headers=[
            "ts",
            "horizon",
            "n_signals",
            "win_rate",
            "avg_win",
            "avg_loss",
            "expectancy",
            "precision_top_decile",
            "max_drawdown_proxy",
            "sharpe_proxy",
        ],
        rows=[
            [
                row.ts.isoformat(),
                row.horizon,
                row.n_signals,
                row.win_rate,
                row.avg_win,
                row.avg_loss,
                row.expectancy,
                row.precision_top_decile,
                row.max_drawdown_proxy,
                row.sharpe_proxy,
            ]
            for row in rows
        ],
    )
    return PlainTextResponse(csv_text, media_type="text/csv")
