from fastapi import APIRouter, Query

from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])
repo = SignalRepository()


@router.get("/latest")
def latest(limit: int = Query(default=25, ge=1, le=200)) -> list[dict]:
    rows = repo.latest_signals(limit=limit)
    return [
        {
            "token_address": row.token_address,
            "ts": row.ts.isoformat(),
            "entry_price": row.entry_price,
            "long_score": row.long_score,
            "short_score": row.short_score,
            "confidence": row.confidence,
            "decision": row.decision,
            "veto": row.veto,
            "reasons": row.reasons_json,
        }
        for row in rows
    ]


@router.get("/top")
def top(decision: str = Query(default="LONG_SETUP", pattern="^(LONG_SETUP|SHORT_SETUP)$"), limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    rows = repo.latest_top(decision=decision, limit=limit)
    return [
        {
            "token_address": row.token_address,
            "ts": row.ts.isoformat(),
            "entry_price": row.entry_price,
            "long_score": row.long_score,
            "short_score": row.short_score,
            "confidence": row.confidence,
            "decision": row.decision,
            "veto": row.veto,
            "reasons": row.reasons_json,
        }
        for row in rows
    ]
