from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.playbook_scanner_service import scanner_service

router = APIRouter(prefix="/narratives", tags=["narratives"])


@router.get("/latest")
def narratives_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_narrative(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "narrative_strength_score": x.narrative_strength_score,
                "meme_clarity_score": x.meme_clarity_score,
                "viral_repeatability_score": x.viral_repeatability_score,
                "cross_source_narrative_score": x.cross_source_narrative_score,
                "paid_vs_organic_narrative_gap": x.paid_vs_organic_narrative_gap,
                "cult_signal_score": x.cult_signal_score,
                "ts": x.ts.isoformat(),
            }
            for x in rows
        ]
    }
