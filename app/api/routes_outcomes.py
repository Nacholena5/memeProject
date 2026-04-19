from fastapi import APIRouter, Query

from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/outcomes", tags=["outcomes"])
repo = SignalRepository()


@router.get("/latest")
def latest(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    rows = repo.latest_outcomes(limit=limit)
    return [
        {
            "score_snapshot_id": row.score_snapshot_id,
            "horizon": row.horizon,
            "ret_pct": row.ret_pct,
            "max_fav_excursion": row.max_fav_excursion,
            "max_adv_excursion": row.max_adv_excursion,
        }
        for row in rows
    ]
