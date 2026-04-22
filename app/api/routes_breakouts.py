from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.playbook_scanner_service import scanner_service

router = APIRouter(prefix="/breakouts", tags=["breakouts"])


@router.get("/latest")
def breakouts_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_breakouts(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "breakout_setup_score": x.breakout_setup_score,
                "consolidation_quality_score": x.consolidation_quality_score,
                "breakout_confirmation_score": x.breakout_confirmation_score,
                "overextension_penalty": x.overextension_penalty,
                "entry_timing_score": x.entry_timing_score,
                "invalidation_quality_score": x.invalidation_quality_score,
                "ts": x.ts.isoformat(),
            }
            for x in rows
        ]
    }
