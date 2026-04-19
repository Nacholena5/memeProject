from app.scoring.score_model import compute_scores


def test_score_ranges() -> None:
    features = {
        "momentum": 0.7,
        "technical_structure": 0.6,
        "liquidity_quality": 0.8,
        "volume_acceleration": 0.9,
        "wallet_flow": 0.5,
        "market_regime": 0.5,
        "safety_quality": 0.9,
        "overextension": 0.3,
        "momentum_loss": 0.2,
        "distribution_signal": 0.2,
        "derivatives_stress": 0.4,
        "bearish_structure": 0.3,
        "market_risk_off": 0.4,
        "liquidity_for_short": 0.7,
        "data_quality": 0.8,
        "signal_alignment": 0.7,
        "market_clarity": 0.6,
    }
    result = compute_scores(features=features, penalties=5.0, reasons={})

    assert 0 <= result.long_score <= 100
    assert 0 <= result.short_score <= 100
    assert 0 <= result.confidence <= 1
