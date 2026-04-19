from dataclasses import dataclass

from app.features.normalization import clamp01


@dataclass
class ScoreResult:
    long_score: float
    short_score: float
    penalties: float
    confidence: float
    reasons: dict


def _long_raw(f: dict) -> float:
    return 100 * (
        0.22 * clamp01(f.get("momentum", 0.0))
        + 0.18 * clamp01(f.get("technical_structure", 0.0))
        + 0.16 * clamp01(f.get("liquidity_quality", 0.0))
        + 0.14 * clamp01(f.get("volume_acceleration", 0.0))
        + 0.10 * clamp01(f.get("wallet_flow", 0.0))
        + 0.10 * clamp01(f.get("market_regime", 0.0))
        + 0.10 * clamp01(f.get("safety_quality", 0.0))
    )


def _short_raw(f: dict) -> float:
    return 100 * (
        0.22 * clamp01(f.get("overextension", 0.0))
        + 0.18 * clamp01(f.get("momentum_loss", 0.0))
        + 0.15 * clamp01(f.get("distribution_signal", 0.0))
        + 0.15 * clamp01(f.get("derivatives_stress", 0.0))
        + 0.12 * clamp01(f.get("bearish_structure", 0.0))
        + 0.10 * clamp01(f.get("market_risk_off", 0.0))
        + 0.08 * clamp01(f.get("liquidity_for_short", 0.0))
    )


def compute_scores(features: dict, penalties: float, reasons: dict) -> ScoreResult:
    long_score = max(0.0, _long_raw(features) - penalties)
    short_score = max(0.0, _short_raw(features) - penalties)

    confidence = clamp01(
        0.4 * features.get("data_quality", 0.0)
        + 0.3 * features.get("signal_alignment", 0.0)
        + 0.3 * features.get("market_clarity", 0.0)
    )

    return ScoreResult(
        long_score=long_score,
        short_score=short_score,
        penalties=penalties,
        confidence=confidence,
        reasons=reasons,
    )
