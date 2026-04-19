from fastapi import APIRouter, HTTPException

from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/tokens", tags=["tokens"])
repo = SignalRepository()


@router.get("/{address}/explain")
def explain(address: str) -> dict:
    rows = repo.latest_signals(limit=300)
    for row in rows:
        if row.token_address.lower() == address.lower():
            return {
                "token_address": row.token_address,
                "ts": row.ts.isoformat(),
                "entry_price": row.entry_price,
                "decision": row.decision,
                "long_score": row.long_score,
                "short_score": row.short_score,
                "confidence": row.confidence,
                "reasons": row.reasons_json,
                "features": row.features_json,
            }
    raise HTTPException(status_code=404, detail="Token not found in latest snapshots")


@router.get("/{address}/history")
def history(address: str, limit: int = 150) -> list[dict]:
    rows = repo.token_signal_history(token_address=address, limit=limit)
    if not rows:
        raise HTTPException(status_code=404, detail="Token history not found")

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
        }
        for row in rows
    ]
