def normalize_security(goplus_data: dict, honeypot_data: dict) -> dict:
    is_honeypot = bool(honeypot_data.get("honeypotResult", {}).get("isHoneypot", False))

    can_mint = str(goplus_data.get("is_mintable", "0")) == "1"
    can_freeze = str(goplus_data.get("can_take_back_ownership", "0")) == "1"

    top10 = float(goplus_data.get("holder_count_top10_ratio", 0.0) or 0.0)
    if top10 <= 1.0:
        top10 *= 100.0

    lp_locked_pct = float(goplus_data.get("lp_locked_total_percent", 0.0) or 0.0)
    if lp_locked_pct <= 1.0:
        lp_locked_pct *= 100.0

    safety_quality = 1.0
    if is_honeypot:
        safety_quality = 0.0
    elif can_mint or can_freeze:
        safety_quality = 0.2
    elif top10 > 60:
        safety_quality = 0.4

    return {
        "honeypot": is_honeypot,
        "can_mint": can_mint,
        "can_freeze": can_freeze,
        "top10_holders_pct": top10,
        "lp_locked_pct": lp_locked_pct,
        "safety_quality": safety_quality,
    }
