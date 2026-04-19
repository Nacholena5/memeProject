from app.config import get_settings


def hard_veto(security: dict, market: dict) -> tuple[bool, list[str]]:
    settings = get_settings()
    reasons: list[str] = []

    if security.get("honeypot", False):
        reasons.append("honeypot")
    if security.get("can_mint", False):
        reasons.append("can_mint")
    if security.get("can_freeze", False):
        reasons.append("can_freeze")

    if float(security.get("lp_locked_pct", 0)) < settings.min_lp_locked_pct:
        reasons.append("lp_lock_low")
    if float(security.get("top10_holders_pct", 100)) > settings.max_top10_holders_pct:
        reasons.append("holder_concentration")

    if float(market.get("liquidity_usd", 0)) < settings.min_liquidity_usd:
        reasons.append("low_liquidity")
    if float(market.get("spread_bps", 10_000)) > settings.max_spread_bps:
        reasons.append("wide_spread")

    return (len(reasons) > 0, reasons)


def risk_penalties(security: dict, market: dict) -> float:
    penalty = 0.0

    top10 = float(security.get("top10_holders_pct", 0.0))
    if top10 > 50:
        penalty += min(12.0, (top10 - 50) * 0.25)

    age_hours = float(market.get("pair_age_hours", 0))
    if age_hours < 12:
        penalty += 6.0

    spread_bps = float(market.get("spread_bps", 0.0))
    if spread_bps > 100:
        penalty += min(8.0, (spread_bps - 100) * 0.05)

    return penalty
