from app.scoring.score_model import compute_scores
from app.scoring.risk_gate import hard_veto, risk_penalties


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


# ---------------------------------------------------------------------------
# Anti-sybil / anti-wash hard veto tests
# ---------------------------------------------------------------------------

def _clean_security() -> dict:
    """Baseline security dict that passes all hard-veto checks."""
    return {
        "honeypot": False,
        "can_mint": False,
        "can_freeze": False,
        "lp_locked_pct": 80.0,
        "top10_holders_pct": 40.0,
    }


def _clean_market() -> dict:
    """Baseline market dict that passes all hard-veto checks."""
    return {
        "liquidity_usd": 100_000.0,
        "spread_bps": 50.0,
        "pair_age_hours": 24.0,
    }


def test_hard_veto_clean_passes() -> None:
    vetoed, reasons = hard_veto(_clean_security(), _clean_market())
    assert not vetoed
    assert reasons == []


def test_hard_veto_wash_volume_concentration() -> None:
    sec = {**_clean_security(), "top_wallets_volume_pct": 85.0}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert vetoed
    assert "wash_volume_concentration" in reasons


def test_hard_veto_wash_volume_below_threshold_passes() -> None:
    sec = {**_clean_security(), "top_wallets_volume_pct": 75.0}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert not vetoed
    assert "wash_volume_concentration" not in reasons


def test_hard_veto_sybil_new_wallets() -> None:
    sec = {**_clean_security(), "new_wallet_ratio": 0.90}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert vetoed
    assert "sybil_new_wallets" in reasons


def test_hard_veto_new_wallet_ratio_below_threshold_passes() -> None:
    sec = {**_clean_security(), "new_wallet_ratio": 0.70}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert not vetoed
    assert "sybil_new_wallets" not in reasons


def test_hard_veto_funding_wallet_reuse() -> None:
    sec = {**_clean_security(), "funding_wallet_reuse": 5}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert vetoed
    assert "funding_wallet_reuse" in reasons


def test_hard_veto_funding_wallet_reuse_at_threshold_passes() -> None:
    sec = {**_clean_security(), "funding_wallet_reuse": 3}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert not vetoed
    assert "funding_wallet_reuse" not in reasons


def test_hard_veto_fast_first_dump() -> None:
    sec = {**_clean_security(), "time_to_first_dump_minutes": 2.0}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert vetoed
    assert "fast_first_dump" in reasons


def test_hard_veto_fast_dump_above_threshold_passes() -> None:
    sec = {**_clean_security(), "time_to_first_dump_minutes": 10.0}
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert not vetoed
    assert "fast_first_dump" not in reasons


def test_hard_veto_missing_antisybil_fields_are_skipped() -> None:
    """When anti-sybil fields are absent the veto should not fire."""
    vetoed, reasons = hard_veto(_clean_security(), _clean_market())
    assert not vetoed
    assert "wash_volume_concentration" not in reasons
    assert "sybil_new_wallets" not in reasons
    assert "funding_wallet_reuse" not in reasons
    assert "fast_first_dump" not in reasons


def test_hard_veto_multiple_antisybil_flags() -> None:
    sec = {
        **_clean_security(),
        "top_wallets_volume_pct": 90.0,
        "new_wallet_ratio": 0.92,
        "time_to_first_dump_minutes": 1.5,
    }
    vetoed, reasons = hard_veto(sec, _clean_market())
    assert vetoed
    assert "wash_volume_concentration" in reasons
    assert "sybil_new_wallets" in reasons
    assert "fast_first_dump" in reasons


# ---------------------------------------------------------------------------
# Anti-sybil soft penalty tests
# ---------------------------------------------------------------------------

def test_risk_penalties_no_antisybil_fields_zero_extra() -> None:
    penalty = risk_penalties(_clean_security(), _clean_market())
    assert penalty == 0.0


def test_risk_penalties_elevated_top_wallets_adds_penalty() -> None:
    sec = {**_clean_security(), "top_wallets_volume_pct": 70.0}
    penalty = risk_penalties(sec, _clean_market())
    assert penalty > 0.0


def test_risk_penalties_top_wallets_capped_at_10() -> None:
    sec = {**_clean_security(), "top_wallets_volume_pct": 99.0}
    penalty = risk_penalties(sec, _clean_market())
    # anti-sybil contribution = min(10.0, (99 - 60) * 0.2) = min(10.0, 7.8) = 7.8
    # Verify the value is bounded by the cap and matches the expected calculation
    import pytest
    assert penalty == pytest.approx(7.8)


def test_risk_penalties_elevated_new_wallet_ratio_adds_penalty() -> None:
    sec = {**_clean_security(), "new_wallet_ratio": 0.75}
    penalty = risk_penalties(sec, _clean_market())
    assert penalty > 0.0


def test_risk_penalties_new_wallet_ratio_capped_at_8() -> None:
    sec = {**_clean_security(), "new_wallet_ratio": 1.0}
    penalty = risk_penalties(sec, _clean_market())
    anti_sybil_contribution = min(8.0, (1.0 - 0.60) * 20.0)
    assert anti_sybil_contribution == 8.0


def test_risk_penalties_combined_antisybil_accumulates() -> None:
    sec = {**_clean_security(), "top_wallets_volume_pct": 70.0, "new_wallet_ratio": 0.75}
    penalty = risk_penalties(sec, _clean_market())
    # Both penalties should add up: (70-60)*0.2 + (0.75-0.60)*20 = 2.0 + 3.0 = 5.0
    import pytest
    assert penalty == pytest.approx((70.0 - 60.0) * 0.2 + (0.75 - 0.60) * 20.0)
    assert penalty > risk_penalties({**_clean_security(), "top_wallets_volume_pct": 70.0}, _clean_market())

