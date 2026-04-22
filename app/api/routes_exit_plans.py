from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.playbook_scanner_service import scanner_service

router = APIRouter(prefix="/exit-plans", tags=["exit-plans"])


@router.get("/latest")
def exit_plans_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_exit_plans(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "entry_zone": x.entry_zone,
                "invalidation_zone": x.invalidation_zone,
                "tp1": x.tp1,
                "tp2": x.tp2,
                "tp3": x.tp3,
                "partial_take_profit_plan": x.partial_take_profit_plan,
                "exit_plan_viability": x.exit_plan_viability,
                "ts": x.ts.isoformat(),
                "payload": x.payload_json,
            }
            for x in rows
        ]
    }
