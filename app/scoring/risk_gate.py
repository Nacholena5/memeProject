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

    # --- Anti-sybil / anti-wash hard rules ---
    # Rule: wash volume concentration — top N wallets explain an outsized share of volume
    top_wallets_volume_pct = security.get("top_wallets_volume_pct")
    if top_wallets_volume_pct is not None:
        if float(top_wallets_volume_pct) > settings.max_top_wallets_volume_pct:
            reasons.append("wash_volume_concentration")

    # Rule: sybil new-wallet flood — most active buyers are brand-new wallets
    new_wallet_ratio = security.get("new_wallet_ratio")
    if new_wallet_ratio is not None:
        if float(new_wallet_ratio) > settings.max_new_wallet_ratio:
            reasons.append("sybil_new_wallets")

    # Rule: coordinated funding source — multiple buyer wallets share the same funder
    funding_wallet_reuse = security.get("funding_wallet_reuse")
    if funding_wallet_reuse is not None:
        if int(funding_wallet_reuse) > settings.max_funding_wallet_reuse:
            reasons.append("funding_wallet_reuse")

    # Rule: fast-dump pattern — early wallets dumped within minutes of launch (insider rug)
    time_to_first_dump = security.get("time_to_first_dump_minutes")
    if time_to_first_dump is not None:
        if float(time_to_first_dump) < settings.min_time_to_first_dump_minutes:
            reasons.append("fast_first_dump")

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

    # --- Anti-sybil / anti-wash soft penalties (approaching but below hard-veto thresholds) ---
    # Wash volume concentration approaching threshold (> 60 % but not yet vetoed)
    top_wallets_volume_pct = security.get("top_wallets_volume_pct")
    if top_wallets_volume_pct is not None:
        twvp = float(top_wallets_volume_pct)
        if twvp > 60.0:
            penalty += min(10.0, (twvp - 60.0) * 0.2)

    # Sybil new-wallet ratio elevated (> 0.60 but not yet vetoed)
    new_wallet_ratio = security.get("new_wallet_ratio")
    if new_wallet_ratio is not None:
        nwr = float(new_wallet_ratio)
        if nwr > 0.60:
            penalty += min(8.0, (nwr - 0.60) * 20.0)

    return penalty
