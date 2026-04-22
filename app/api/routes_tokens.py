from fastapi import APIRouter, HTTPException

from app.services.playbook_scanner_service import scanner_service
from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/tokens", tags=["tokens"])
repo = SignalRepository()


def _short_address(address: str) -> str:
    if not address:
        return "N/D"
    if len(address) <= 12:
        return address
    return f"{address[:6]}...{address[-4:]}"


def _symbol_for_row(row: object) -> str:
    raw = str(getattr(row, "token_symbol", "") or "").strip().upper()
    if raw and raw not in {"TOKEN", "UNK", "UNKNOWN", "N/A"}:
        return raw

    name = str(getattr(row, "token_name", "") or "").strip()
    if name and name.lower() not in {"token sin nombre", "unknown token", "token"}:
        return name[:10].upper()

    address = str(getattr(row, "token_address", "") or "")
    return f"TK-{address[:4].upper()}" if address else "TOKEN"


def _name_for_row(row: object, symbol: str) -> str:
    raw_name = str(getattr(row, "token_name", "") or "").strip()
    if raw_name and raw_name.lower() not in {"token sin nombre", "unknown token", "token"}:
        return raw_name

    return f"{symbol} token" if symbol else f"Token {_short_address(str(getattr(row, 'token_address', '') or ''))}"


def _serialize_identity(row: object) -> dict:
    symbol = _symbol_for_row(row)
    return {
        "token_address": row.token_address,
        "symbol": symbol,
        "name": _name_for_row(row, symbol),
        "chain": str(getattr(row, "token_chain", "") or "solana").lower(),
        "principal_pair": str(getattr(row, "principal_pair", "") or ""),
        "metadata_source": str(getattr(row, "metadata_source", "unknown") or "unknown").lower(),
        "metadata_confidence": str(getattr(row, "metadata_confidence", "unverified") or "unverified").lower(),
        "metadata_is_fallback": bool(getattr(row, "metadata_is_fallback", False)),
        "metadata_last_source": str(getattr(row, "metadata_last_source", "unknown") or "unknown").lower(),
        "metadata_last_validated_at": getattr(row, "metadata_last_validated_at", None).isoformat() if getattr(row, "metadata_last_validated_at", None) else None,
        "metadata_conflict": bool(getattr(row, "metadata_conflict", False)),
    }


@router.get("/{address}/explain")
def explain(address: str) -> dict:
    rows = repo.latest_signals(limit=300)
    for row in rows:
        if row.token_address.lower() == address.lower():
            identity = _serialize_identity(row)
            paid_attention_snapshot = scanner_service.repo.token_paid_attention_latest(address)
            exit_plan_snapshot = scanner_service.repo.token_exit_plan_latest(address)
            return {
                **identity,
                "ts": row.ts.isoformat(),
                "entry_price": row.entry_price,
                "decision": row.decision,
                "long_score": row.long_score,
                "short_score": row.short_score,
                "confidence": row.confidence,
                "reasons": row.reasons_json,
                "features": row.features_json,
                "paid_attention": {
                    "boost_intensity": paid_attention_snapshot.boost_intensity if paid_attention_snapshot else None,
                    "paid_attention_high": paid_attention_snapshot.paid_attention_high if paid_attention_snapshot else None,
                    "promo_flow_divergence": paid_attention_snapshot.promo_flow_divergence if paid_attention_snapshot else None,
                    "paid_vs_organic_gap": paid_attention_snapshot.paid_vs_organic_gap if paid_attention_snapshot else None,
                },
                "exit_plan": {
                    "entry_zone": exit_plan_snapshot.entry_zone if exit_plan_snapshot else None,
                    "invalidation_zone": exit_plan_snapshot.invalidation_zone if exit_plan_snapshot else None,
                    "tp1": exit_plan_snapshot.tp1 if exit_plan_snapshot else None,
                    "tp2": exit_plan_snapshot.tp2 if exit_plan_snapshot else None,
                    "tp3": exit_plan_snapshot.tp3 if exit_plan_snapshot else None,
                    "partial_take_profit_plan": exit_plan_snapshot.partial_take_profit_plan if exit_plan_snapshot else None,
                    "exit_plan_viability": exit_plan_snapshot.exit_plan_viability if exit_plan_snapshot else None,
                },
            }
    raise HTTPException(status_code=404, detail="Token not found in latest snapshots")


@router.get("/{address}/history")
def history(address: str, limit: int = 150) -> list[dict]:
    rows = repo.token_signal_history(token_address=address, limit=limit)
    if not rows:
        raise HTTPException(status_code=404, detail="Token history not found")

    return [
        {
            **_serialize_identity(row),
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


@router.get("/{address}/exit-plan")
def exit_plan(address: str) -> dict:
    snapshot = scanner_service.repo.token_exit_plan_latest(address)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Exit plan not found for token")
    return {
        "token_address": snapshot.token_address,
        "scan_session_id": snapshot.scan_session_id,
        "entry_zone": snapshot.entry_zone,
        "invalidation_zone": snapshot.invalidation_zone,
        "tp1": snapshot.tp1,
        "tp2": snapshot.tp2,
        "tp3": snapshot.tp3,
        "partial_take_profit_plan": snapshot.partial_take_profit_plan,
        "exit_plan_viability": snapshot.exit_plan_viability,
        "ts": snapshot.ts.isoformat(),
        "payload": snapshot.payload_json,
    }
