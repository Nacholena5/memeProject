from fastapi import APIRouter, Query

from app.services.data_quality_service import DataQualityService
from app.services.operability_service import OperabilityService
from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])
repo = SignalRepository()
operability = OperabilityService()
quality_service = DataQualityService()


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

    address = str(getattr(row, "token_address", "") or "")
    return f"{symbol} token" if symbol else f"Token {_short_address(address)}"


def _risk_label_from_row(row: object) -> str:
    confidence = float(getattr(row, "confidence", 0) or 0)
    reasons_json = getattr(row, "reasons_json", None) or {}
    penalties = float(reasons_json.get("penalties", 0) or 0)
    veto_reasons = reasons_json.get("veto_reasons") or []
    has_veto = bool(getattr(row, "veto", False))

    if has_veto or confidence < 0.62 or penalties > 8 or len(veto_reasons) > 0:
        return "alto"
    if confidence < 0.75 or penalties > 4:
        return "medio"
    return "bajo"


def _serialize_signal(row: object, data_quality_degraded: bool = False) -> dict:
    symbol = _symbol_for_row(row)
    name = _name_for_row(row, symbol)
    reasons_json = getattr(row, "reasons_json", None) or {}
    veto_reasons = reasons_json.get("veto_reasons", [])

    operability_result = operability.classify(
        decision=row.decision,
        veto=bool(row.veto),
        score_long=float(row.long_score or 0),
        score_short=float(row.short_score or 0),
        confidence=float(row.confidence or 0),
        metadata_confidence=str(getattr(row, "metadata_confidence", "unverified") or "unverified").lower(),
        metadata_is_fallback=bool(getattr(row, "metadata_is_fallback", False)),
        risk_label=_risk_label_from_row(row),
        liquidity_usd=float(getattr(row, "liquidity_usd", 0) or 0),
        identity_quality_score=int(getattr(row, "identity_quality_score", 50) or 50),
        veto_reasons=veto_reasons,
        data_quality_degraded=data_quality_degraded,
    )

    return {
        "token_address": row.token_address,
        "symbol": symbol,
        "name": name,
        "chain": str(getattr(row, "token_chain", "") or "solana").lower(),
        "principal_pair": str(getattr(row, "principal_pair", "") or ""),
        "metadata_source": str(getattr(row, "metadata_source", "unknown") or "unknown").lower(),
        "metadata_confidence": str(getattr(row, "metadata_confidence", "unverified") or "unverified").lower(),
        "metadata_is_fallback": bool(getattr(row, "metadata_is_fallback", False)),
        "metadata_last_source": str(getattr(row, "metadata_last_source", "unknown") or "unknown").lower(),
        "metadata_last_validated_at": getattr(row, "metadata_last_validated_at", None).isoformat() if getattr(row, "metadata_last_validated_at", None) else None,
        "metadata_conflict": bool(getattr(row, "metadata_conflict", False)),
        "ts": row.ts.isoformat(),
        "entry_price": row.entry_price,
        "long_score": row.long_score,
        "short_score": row.short_score,
        "confidence": row.confidence,
        "decision": row.decision,
        "veto": row.veto,
        "reasons": row.reasons_json,
        "operability_status": operability_result.status,
        "operability_can_long": operability_result.can_long,
        "operability_can_short": operability_result.can_short,
        "operability_blocker": operability_result.blocker,
        "operability_reason": operability_result.reason,
        "operability_why_not": operability_result.why_not,
    }


@router.get("/latest")
def latest(
    limit: int = Query(default=25, ge=1, le=200),
    q: str | None = Query(default=None, min_length=1, max_length=64),
) -> list[dict]:
    rows = repo.latest_signals(limit=limit, query=q)
    quality = quality_service.compute()
    data_quality_degraded = quality.get("status") != "ok"
    return [_serialize_signal(row, data_quality_degraded=data_quality_degraded) for row in rows]


@router.get("/top")
def top(
    decision: str = Query(default="LONG_SETUP", pattern="^(LONG_SETUP|SHORT_SETUP)$"),
    limit: int = Query(default=10, ge=1, le=50),
    q: str | None = Query(default=None, min_length=1, max_length=64),
) -> list[dict]:
    rows = repo.latest_top(decision=decision, limit=limit, query=q)
    quality = quality_service.compute()
    data_quality_degraded = quality.get("status") != "ok"
    return [_serialize_signal(row, data_quality_degraded=data_quality_degraded) for row in rows]
