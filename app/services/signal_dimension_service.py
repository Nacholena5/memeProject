from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


@dataclass
class SignalDimensionResult:
    whale: dict[str, float]
    social: dict[str, float]
    demand: dict[str, float]
    narrative: dict[str, float]
    breakout: dict[str, float]
    paid_attention: dict[str, float | bool]
    event_signal: dict[str, float]
    composite: dict[str, float | str]


def compute_signal_dimensions(validation: dict[str, Any], score_payload: dict[str, Any], event_signal: dict[str, Any] | None = None) -> SignalDimensionResult:
    """Compute conservative signal dimensions from existing on-chain/market evidence.

    These dimensions are secondary inputs: they can improve priority/confidence only when
    core constraints (risk, liquidity, identity, data quality) are already acceptable.
    """
    flags = validation.get("flags") or []
    status = validation.get("status") or ""
    buys = float(validation.get("buys_24h") or 0.0)
    sells = float(validation.get("sells_24h") or 0.0)
    volume = float(validation.get("volume_24h") or 0.0)
    mcap = float(validation.get("market_cap") or 0.0)
    paid_orders = float(validation.get("paid_orders_24h") or 0.0)
    activity_score = float(validation.get("activity_score") or 0.0)
    boosts_active = float(validation.get("boosts_active") or 0.0)
    price_change_1h = float(validation.get("price_change_1h") or 0.0)
    price_change_5m = float(validation.get("price_change_5m") or 0.0)

    demand_base = _clamp((buys * 3.0 + volume / 1200.0 + activity_score * 7.0) / 4.2)
    buy_sell_ratio = buys / max(1.0, sells)
    organic_flow_bonus = 10.0 if "organic_flow_ok" in flags else 0.0
    wash_penalty = 22.0 if "suspicious_volume_vertical" in flags else 0.0
    low_txs_penalty = 15.0 if "low_txs" in flags else 0.0

    whale_accumulation_score = _clamp(demand_base + (buy_sell_ratio - 1.0) * 18.0 + organic_flow_bonus - wash_penalty)
    smart_wallet_presence_score = _clamp(activity_score * 10.0 + min(18.0, volume / 10000.0))
    net_whale_inflow = _clamp((buy_sell_ratio - 1.0) * 40.0 + 50.0)
    repeated_buyer_score = _clamp(min(100.0, buys * 1.6))
    insider_risk_score = _clamp((paid_orders * 9.0) + (25.0 if "suspicious_volume_vertical" in flags else 0.0))
    dev_sell_pressure_score = _clamp((18.0 if buy_sell_ratio < 0.9 else 0.0) + (15.0 if "new_pair" in flags else 0.0))

    social_velocity_score = _clamp(boosts_active * 22.0 + max(0.0, price_change_5m) * 6.0)
    community_growth_score = _clamp(min(100.0, buys * 1.1 + boosts_active * 8.0))
    organic_engagement_score = _clamp(65.0 if "organic_flow_ok" in flags else 35.0)
    bot_suspicion_score = _clamp((35.0 if paid_orders >= 2 else 10.0) + (20.0 if "suspicious_volume_vertical" in flags else 0.0))
    narrative_repetition_score = _clamp(30.0 + boosts_active * 9.0)
    social_wallet_divergence_score = _clamp(abs(social_velocity_score - whale_accumulation_score) * 0.6)

    tx_count_acceleration = _clamp((buys + sells) * 1.2)
    organic_volume_score = _clamp(75.0 if "organic_flow_ok" in flags else 40.0)
    wash_trading_suspicion_score = _clamp((30.0 if "suspicious_volume_vertical" in flags else 5.0) + paid_orders * 8.0)
    buyer_distribution_score = _clamp(65.0 if buy_sell_ratio > 1.2 else 45.0)
    trade_continuity_score = _clamp(55.0 + min(35.0, activity_score * 9.0))
    transaction_demand_score = _clamp(
        demand_base + organic_flow_bonus - wash_penalty - low_txs_penalty + (buy_sell_ratio - 1.0) * 14.0
    )

    meme_clarity_score = _clamp(40.0 + boosts_active * 10.0)
    viral_repeatability_score = _clamp(45.0 + max(0.0, price_change_1h) * 1.8)
    cross_source_narrative_score = _clamp(50.0 + (10.0 if boosts_active >= 2 else 0.0))
    paid_vs_organic_narrative_gap = _clamp(max(0.0, paid_orders * 12.0 - 20.0))
    cult_signal_score = _clamp((meme_clarity_score + viral_repeatability_score) / 2.0)
    narrative_strength_score = _clamp(
        0.35 * meme_clarity_score
        + 0.3 * viral_repeatability_score
        + 0.2 * cross_source_narrative_score
        + 0.15 * cult_signal_score
        - 0.25 * paid_vs_organic_narrative_gap
    )

    overextension_penalty = _clamp(max(0.0, price_change_1h - 16.0) * 2.2 + max(0.0, price_change_5m - 4.0) * 3.0)
    consolidation_quality_score = _clamp(70.0 if abs(price_change_5m) < 3.0 else 45.0)
    breakout_confirmation_score = _clamp(50.0 + min(30.0, (buy_sell_ratio - 1.0) * 22.0) + activity_score * 8.0)
    entry_timing_score = _clamp(65.0 - overextension_penalty * 0.45 + (12.0 if "organic_flow_ok" in flags else 0.0))
    invalidation_quality_score = _clamp(60.0 + (12.0 if mcap > 25000 else 0.0) - (10.0 if "new_pair" in flags else 0.0))
    breakout_setup_score = _clamp(
        0.28 * consolidation_quality_score
        + 0.3 * breakout_confirmation_score
        + 0.25 * entry_timing_score
        + 0.17 * invalidation_quality_score
    )

    boost_intensity = _clamp(boosts_active * 16.0 + paid_orders * 8.0 + max(0.0, price_change_1h) * 1.2)
    paid_vs_organic_gap = _clamp(max(0.0, paid_orders * 12.0 - activity_score * 4.5))
    paid_attention_high = paid_orders >= 3 or boosts_active >= 2.5 or paid_vs_organic_gap >= 45.0
    promo_flow_divergence = paid_attention_high and buy_sell_ratio < 1.05

    social_momentum_score = _clamp(
        0.36 * social_velocity_score + 0.24 * community_growth_score + 0.2 * organic_engagement_score - 0.2 * bot_suspicion_score
    )

    speculative_momentum_score = _clamp(
        0.2 * whale_accumulation_score
        + 0.2 * social_momentum_score
        + 0.25 * transaction_demand_score
        + 0.15 * narrative_strength_score
        + 0.2 * entry_timing_score
    )

    gate_notes = "ok"
    if status == "discarded" or transaction_demand_score < 35.0:
        gate_notes = "demand_weak"
    elif bot_suspicion_score >= 65.0 and social_wallet_divergence_score >= 35.0:
        gate_notes = "social_bot_divergence"
    elif overextension_penalty >= 45.0:
        gate_notes = "overextended"

    return SignalDimensionResult(
        whale={
            "whale_accumulation_score": whale_accumulation_score,
            "smart_wallet_presence_score": smart_wallet_presence_score,
            "net_whale_inflow": net_whale_inflow,
            "repeated_buyer_score": repeated_buyer_score,
            "insider_risk_score": insider_risk_score,
            "dev_sell_pressure_score": dev_sell_pressure_score,
        },
        social={
            "social_velocity_score": social_velocity_score,
            "community_growth_score": community_growth_score,
            "organic_engagement_score": organic_engagement_score,
            "bot_suspicion_score": bot_suspicion_score,
            "narrative_repetition_score": narrative_repetition_score,
            "social_wallet_divergence_score": social_wallet_divergence_score,
        },
        demand={
            "transaction_demand_score": transaction_demand_score,
            "tx_count_acceleration": tx_count_acceleration,
            "organic_volume_score": organic_volume_score,
            "wash_trading_suspicion_score": wash_trading_suspicion_score,
            "buyer_distribution_score": buyer_distribution_score,
            "trade_continuity_score": trade_continuity_score,
        },
        narrative={
            "narrative_strength_score": narrative_strength_score,
            "meme_clarity_score": meme_clarity_score,
            "viral_repeatability_score": viral_repeatability_score,
            "cross_source_narrative_score": cross_source_narrative_score,
            "paid_vs_organic_narrative_gap": paid_vs_organic_narrative_gap,
            "cult_signal_score": cult_signal_score,
        },
        breakout={
            "breakout_setup_score": breakout_setup_score,
            "consolidation_quality_score": consolidation_quality_score,
            "breakout_confirmation_score": breakout_confirmation_score,
            "overextension_penalty": overextension_penalty,
            "entry_timing_score": entry_timing_score,
            "invalidation_quality_score": invalidation_quality_score,
        },
        paid_attention={
            "boost_intensity": boost_intensity,
            "paid_attention_high": paid_attention_high,
            "promo_flow_divergence": promo_flow_divergence,
            "paid_vs_organic_gap": paid_vs_organic_gap,
        },
        event_signal={
            "event_relevance_score": float(event_signal.get("event_relevance_score", 0.0)) if event_signal else 0.0,
            "catalyst_probability_score": float(event_signal.get("catalyst_probability_score", 0.0)) if event_signal else 0.0,
            "catalyst_urgency_score": float(event_signal.get("catalyst_urgency_score", 0.0)) if event_signal else 0.0,
            "event_sentiment_score": float(event_signal.get("event_sentiment_score", 0.0)) if event_signal else 0.0,
            "event_volume_score": float(event_signal.get("event_volume_score", 0.0)) if event_signal else 0.0,
            "consensus_shift_score": float(event_signal.get("consensus_shift_score", 0.0)) if event_signal else 0.0,
            "macro_event_risk_score": float(event_signal.get("macro_event_risk_score", 0.0)) if event_signal else 0.0,
            "narrative_alignment_score": float(event_signal.get("narrative_alignment_score", 0.0)) if event_signal else 0.0,
        },
        composite={
            "whale_accumulation_score": whale_accumulation_score,
            "social_momentum_score": social_momentum_score,
            "demand_quality_score": transaction_demand_score,
            "narrative_strength_score": narrative_strength_score,
            "breakout_timing_score": entry_timing_score,
            "speculative_momentum_score": speculative_momentum_score,
            "gate_notes": gate_notes,
        },
    )
