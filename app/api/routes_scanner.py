from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.services.playbook_scanner_service import (
    discarded_today_payload,
    scanner_service,
    watchlist_today_payload,
)

router = APIRouter(prefix="/scanner", tags=["scanner"])


def _serialize_session_summary(session) -> dict | None:
    if session is None:
        return None
    return {
        "scan_session_id": session.id,
        "status": session.status,
        "degraded": session.degraded,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "finished_at": session.finished_at.isoformat() if session.finished_at else None,
        "watchlist_count": session.watchlist_count,
        "discarded_count": session.discarded_count,
        "sources": session.source_summary_json,
        "notes": session.notes_json,
    }


@router.post("/run")
async def run_scanner_now() -> dict:
    result = await scanner_service.run_scan(trigger="manual")
    if result.get("status") == "busy":
        raise HTTPException(status_code=409, detail="Scanner already running")
    return result


@router.get("/discovery/latest")
def discovery_latest() -> dict:
    session = scanner_service.repo.latest_session()
    if not session:
        return {"status": "empty", "rows": []}

    rows = scanner_service.repo.discovery_for_session(session.id)
    payload = [
        {
            "token_address": x.token_address,
            "symbol": x.symbol,
            "metadata_source": x.metadata_source,
            "metadata_confidence": x.metadata_confidence,
            "metadata_is_fallback": x.metadata_is_fallback,
            "metadata_last_source": x.metadata_last_source,
            "metadata_last_validated_at": x.metadata_last_validated_at.isoformat() if x.metadata_last_validated_at else None,
            "metadata_conflict": x.metadata_conflict,
            "source": x.source,
            "age_minutes": x.token_age_minutes,
            "liquidity_usd": x.liquidity_usd,
            "volume_1h_usd": x.volume_1h_usd,
            "transactions_1h": x.transactions_1h,
            "buys_sells_ratio": x.buys_sells_ratio,
            "market_cap_usd": x.market_cap_usd,
            "price_change_1h": x.price_change_1h,
            "volume_acceleration": x.volume_acceleration,
            "ts": x.detected_at.isoformat(),
            "scan_session_id": x.scan_session_id,
        }
        for x in rows
    ]
    return {
        "status": "ok",
        "scan_session_id": session.id,
        "scan_status": session.status,
        "degraded": session.degraded,
        "rows": payload,
    }


@router.get("/watchlist/today")
def watchlist_today(
    q: str | None = Query(default=None),
    identity: str | None = Query(default=None, description="confirmed|inferred|fallback|unverified"),
) -> dict:
    return watchlist_today_payload(q=q, identity=identity)


@router.get("/watchlist/history")
def watchlist_history(limit: int = Query(default=20, ge=1, le=120)) -> dict:
    sessions = scanner_service.repo.sessions_history(limit=limit)
    return {
        "rows": [
            {
                "scan_session_id": s.id,
                "started_at": s.started_at.isoformat(),
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "status": s.status,
                "degraded": s.degraded,
                "discovered": s.discovered_count,
                "validated": s.validated_count,
                "classified": s.classified_count,
                "watchlist": s.watchlist_count,
                "discarded": s.discarded_count,
            }
            for s in sessions
        ]
    }


@router.get("/discarded/today")
def discarded_today() -> dict:
    return discarded_today_payload()


@router.get("/funnel/latest")
def funnel_latest() -> dict:
    current = scanner_service.repo.latest_session()
    latest_valid = scanner_service.repo.latest_valid_session()
    if current and current.status == "completed" and not current.degraded and current.watchlist_count > 0:
        session = current
        source = "current"
    else:
        session = latest_valid
        source = "latest_valid" if latest_valid is not None else "none"

    if not session:
        return {"status": "empty"}

    watch_rows = scanner_service.repo.watchlist_for_session(session.id)
    discarded_rows = scanner_service.repo.discarded_for_session(session.id)

    blocked_identity = 0
    blocked_risk = 0
    blocked_liquidity = 0
    degraded_quality = 0
    operable = 0
    watchlist_only = 0
    no_trade = 0

    for row in watch_rows:
        category = str(row.category or "")
        reason = str(row.main_reason or "").lower()
        metadata_confidence = str(row.metadata_confidence or "").lower()
        risk_label = str(row.risk_label or "").lower()

        if category == "LONG ahora":
            operable += 1
        else:
            watchlist_only += 1

        if metadata_confidence in {"fallback", "unverified"}:
            blocked_identity += 1
        if risk_label == "alto" or "riesgo" in reason:
            blocked_risk += 1
        if "liquidez" in reason or "liquidity" in reason:
            blocked_liquidity += 1
        if "quality" in reason or "degrad" in reason:
            degraded_quality += 1

    for row in discarded_rows:
        reason = str(row.discard_reason or "").lower()
        metadata_confidence = str(row.metadata_confidence or "").lower()

        no_trade += 1
        if metadata_confidence in {"fallback", "unverified"}:
            blocked_identity += 1
        if "riesgo" in reason:
            blocked_risk += 1
        if "liquidez" in reason or "liquidity" in reason:
            blocked_liquidity += 1
        if "quality" in reason or "degrad" in reason:
            degraded_quality += 1

    blocker_counts = {
        "identity": blocked_identity,
        "risk": blocked_risk,
        "liquidity": blocked_liquidity,
        "data_quality": degraded_quality,
    }
    dominant_blocker = max(blocker_counts, key=blocker_counts.get) if any(blocker_counts.values()) else "none"

    return {
        "status": "ok",
        "source": source,
        "scan_session_id": session.id,
        "scan_status": session.status,
        "degraded": session.degraded,
        "steps": {
            "birdeye_detected": session.discovered_count,
            "dex_validated": session.validated_count,
            "classified": session.classified_count,
            "blocked_identity": blocked_identity,
            "blocked_risk": blocked_risk,
            "blocked_liquidity": blocked_liquidity,
            "degraded_quality": degraded_quality,
            "watchlist": session.watchlist_count,
            "operable": operable,
            "watchlist_only": watchlist_only,
            "no_trade": no_trade,
            "discarded": session.discarded_count,
        },
        "blockers": blocker_counts,
        "dominant_blocker": dominant_blocker,
        "sources": session.source_summary_json,
        "notes": session.notes_json,
        "started_at": session.started_at.isoformat(),
        "finished_at": session.finished_at.isoformat() if session.finished_at else None,
    }


@router.get("/token/{address}")
def scanner_token(address: str) -> dict:
    latest_watch = scanner_service.repo.token_watchlist_latest(address)
    latest_discard = scanner_service.repo.token_discarded_latest(address)

    if latest_watch is None and latest_discard is None:
        raise HTTPException(status_code=404, detail="Token not found in scanner history")

    if latest_watch is not None:
        return {
            "token_address": latest_watch.token_address,
            "symbol": latest_watch.symbol,
            "metadata_source": latest_watch.metadata_source,
            "metadata_confidence": latest_watch.metadata_confidence,
            "metadata_is_fallback": latest_watch.metadata_is_fallback,
            "metadata_last_source": latest_watch.metadata_last_source,
            "metadata_last_validated_at": latest_watch.metadata_last_validated_at.isoformat() if latest_watch.metadata_last_validated_at else None,
            "metadata_conflict": latest_watch.metadata_conflict,
            "category": latest_watch.category,
            "score_long": latest_watch.score_long,
            "score_short": latest_watch.score_short,
            "confidence": latest_watch.confidence,
            "risk_label": latest_watch.risk_label,
            "risk_value": latest_watch.risk_value,
            "liquidity_usd": latest_watch.liquidity_usd,
            "main_reason": latest_watch.main_reason,
            "explanation": latest_watch.explanation,
            "payload": latest_watch.payload_json,
            "scan_session_id": latest_watch.scan_session_id,
            "ts": latest_watch.created_at.isoformat(),
        }

    assert latest_discard is not None
    return {
        "token_address": latest_discard.token_address,
        "symbol": latest_discard.symbol,
        "metadata_source": latest_discard.metadata_source,
        "metadata_confidence": latest_discard.metadata_confidence,
        "metadata_is_fallback": latest_discard.metadata_is_fallback,
        "metadata_last_source": latest_discard.metadata_last_source,
        "metadata_last_validated_at": latest_discard.metadata_last_validated_at.isoformat() if latest_discard.metadata_last_validated_at else None,
        "metadata_conflict": latest_discard.metadata_conflict,
        "category": latest_discard.category,
        "discard_reason": latest_discard.discard_reason,
        "flags": latest_discard.flags_json,
        "scan_session_id": latest_discard.scan_session_id,
        "ts": latest_discard.created_at.isoformat(),
    }


@router.get("/token/{address}/signals")
def scanner_token_signals(address: str) -> dict:
    latest_watch = scanner_service.repo.token_watchlist_latest(address)
    latest_discard = scanner_service.repo.token_discarded_latest(address)
    if latest_watch is None and latest_discard is None:
        raise HTTPException(status_code=404, detail="Token not found in scanner history")

    signals = scanner_service.repo.token_latest_signals(address)
    payload = latest_watch.payload_json if latest_watch is not None else {}
    return {
        "token_address": address,
        "category": latest_watch.category if latest_watch is not None else latest_discard.category,
        "main_reason": latest_watch.main_reason if latest_watch is not None else latest_discard.discard_reason,
        "explanation": latest_watch.explanation if latest_watch is not None else "",
        "signal_dimensions": payload.get("signal_dimensions", {}),
        "paid_attention": payload.get("paid_attention", {}),
        "exit_plan": payload.get("exit_plan", {}),
        "actionable_explanation": payload.get("actionable_explanation", ""),
        "signals_snapshot": signals,
        "metadata": {
            "confidence": (latest_watch.metadata_confidence if latest_watch is not None else latest_discard.metadata_confidence),
            "source": (latest_watch.metadata_source if latest_watch is not None else latest_discard.metadata_source),
            "conflict": (latest_watch.metadata_conflict if latest_watch is not None else latest_discard.metadata_conflict),
        },
    }


@router.get("/paid-attention/latest")
def paid_attention_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_paid_attention(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "boost_intensity": x.boost_intensity,
                "paid_attention_high": x.paid_attention_high,
                "promo_flow_divergence": x.promo_flow_divergence,
                "paid_vs_organic_gap": x.paid_vs_organic_gap,
                "ts": x.ts.isoformat(),
                "payload": x.payload_json,
            }
            for x in rows
        ]
    }


@router.get("/events/latest")
def events_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_event_sentiments(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "event_relevance_score": x.event_relevance_score,
                "catalyst_probability_score": x.catalyst_probability_score,
                "catalyst_urgency_score": x.catalyst_urgency_score,
                "event_sentiment_score": x.event_sentiment_score,
                "event_volume_score": x.event_volume_score,
                "consensus_shift_score": x.consensus_shift_score,
                "macro_event_risk_score": x.macro_event_risk_score,
                "narrative_alignment_score": x.narrative_alignment_score,
                "ts": x.ts.isoformat(),
                "payload": x.payload_json,
            }
            for x in rows
        ]
    }


@router.get("/token/{address}/paid-attention")
def scanner_token_paid_attention(address: str) -> dict:
    row = scanner_service.repo.token_paid_attention_latest(address)
    if row is None:
        raise HTTPException(status_code=404, detail="Paid attention snapshot not found for token")
    return {
        "token_address": row.token_address,
        "scan_session_id": row.scan_session_id,
        "boost_intensity": row.boost_intensity,
        "paid_attention_high": row.paid_attention_high,
        "promo_flow_divergence": row.promo_flow_divergence,
        "paid_vs_organic_gap": row.paid_vs_organic_gap,
        "ts": row.ts.isoformat(),
        "payload": row.payload_json,
    }


@router.get("/whales/latest")
def whales_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_whales(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "whale_accumulation_score": x.whale_accumulation_score,
                "smart_wallet_presence_score": x.smart_wallet_presence_score,
                "net_whale_inflow": x.net_whale_inflow,
                "repeated_buyer_score": x.repeated_buyer_score,
                "insider_risk_score": x.insider_risk_score,
                "dev_sell_pressure_score": x.dev_sell_pressure_score,
                "ts": x.ts.isoformat(),
            }
            for x in rows
        ]
    }


@router.get("/social/latest")
def social_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_social(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "social_velocity_score": x.social_velocity_score,
                "community_growth_score": x.community_growth_score,
                "organic_engagement_score": x.organic_engagement_score,
                "bot_suspicion_score": x.bot_suspicion_score,
                "narrative_repetition_score": x.narrative_repetition_score,
                "social_wallet_divergence_score": x.social_wallet_divergence_score,
                "ts": x.ts.isoformat(),
            }
            for x in rows
        ]
    }


@router.get("/narrative/latest")
def narrative_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
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


@router.get("/demand/latest")
def demand_latest(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    rows = scanner_service.repo.latest_demand(limit=limit)
    return {
        "rows": [
            {
                "token_address": x.token_address,
                "scan_session_id": x.scan_session_id,
                "transaction_demand_score": x.transaction_demand_score,
                "tx_count_acceleration": x.tx_count_acceleration,
                "organic_volume_score": x.organic_volume_score,
                "wash_trading_suspicion_score": x.wash_trading_suspicion_score,
                "buyer_distribution_score": x.buyer_distribution_score,
                "trade_continuity_score": x.trade_continuity_score,
                "ts": x.ts.isoformat(),
            }
            for x in rows
        ]
    }


@router.get("/breakouts/latest")
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


@router.get("/status")
def scanner_status() -> dict:
    latest = scanner_service.repo.latest_session()
    latest_valid = scanner_service.repo.latest_valid_session()
    return {
        "running": scanner_service.is_running(),
        "today": date.today().isoformat(),
        "latest": _serialize_session_summary(latest),
        "latest_valid": _serialize_session_summary(latest_valid),
    }
