from app.features.normalization import clamp01


def build_market_context() -> dict:
    # Placeholder for BTC/SOL/ETH trend and sector state. For MVP we keep deterministic defaults.
    return {
        "market_regime": 0.55,
        "market_risk_off": 0.35,
        "market_clarity": 0.60,
    }


def build_derivatives_context(coinglass_payload: dict) -> dict:
    if not coinglass_payload:
        return {
            "derivatives_stress": 0.15,
            "shortable": False,
            "liquidity_for_short": 0.10,
        }

    return {
        "derivatives_stress": clamp01(0.55),
        "shortable": True,
        "liquidity_for_short": clamp01(0.60),
    }
