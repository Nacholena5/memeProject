from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.playbook_scanner_service import scanner_service

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/top")
def wallets_top(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_wallet_flows(limit=limit)
    payload = [
        {
            "token_address": row.token_address,
            "scan_session_id": row.scan_session_id,
            "wallet_flow_score": row.wallet_flow_score,
            "whale_accumulation_score": row.whale_accumulation_score,
            "smart_wallet_presence_score": row.smart_wallet_presence_score,
            "net_whale_inflow": row.net_whale_inflow,
            "repeated_buyer_score": row.repeated_buyer_score,
            "insider_risk_score": row.insider_risk_score,
            "dev_sell_pressure_score": row.dev_sell_pressure_score,
            "labeled_wallet_count": row.labeled_wallet_count,
            "ts": row.ts.isoformat(),
            "notes": row.payload_json,
        }
        for row in rows
    ]
    payload.sort(key=lambda x: x["wallet_flow_score"], reverse=True)
    return {"rows": payload}


@router.get("/token/{address}")
def wallets_for_token(address: str, limit: int = Query(default=40, ge=1, le=200)) -> dict:
    rows = scanner_service.repo.wallet_flow_for_token(token_address=address, limit=limit)
    holder = scanner_service.repo.latest_holder_distribution_for_token(token_address=address)

    history = [
        {
            "wallet_flow_score": row.wallet_flow_score,
            "whale_accumulation_score": row.whale_accumulation_score,
            "smart_wallet_presence_score": row.smart_wallet_presence_score,
            "net_whale_inflow": row.net_whale_inflow,
            "repeated_buyer_score": row.repeated_buyer_score,
            "insider_risk_score": row.insider_risk_score,
            "dev_sell_pressure_score": row.dev_sell_pressure_score,
            "labeled_wallet_count": row.labeled_wallet_count,
            "ts": row.ts.isoformat(),
        }
        for row in rows
    ]

    holder_distribution = (
        {
            "top10_holders_pct": holder.top10_holders_pct,
            "top25_holders_pct": holder.top25_holders_pct,
            "holder_concentration_score": holder.holder_concentration_score,
            "suspicious_cluster_score": holder.suspicious_cluster_score,
            "connected_wallet_clusters": holder.connected_wallet_clusters,
            "organic_distribution_score": holder.organic_distribution_score,
            "cluster_preview": (holder.payload_json or {}).get("cluster_preview", []),
            "ts": holder.ts.isoformat(),
        }
        if holder is not None
        else {}
    )

    return {
        "token_address": address,
        "history": history,
        "holder_distribution": holder_distribution,
    }
