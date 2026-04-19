from app.features.normalization import clamp01


def _extract_largest_accounts(largest_accounts_result: dict) -> list[dict]:
    if not largest_accounts_result:
        return []
    value = largest_accounts_result.get("value", [])
    return value if isinstance(value, list) else []


def _extract_signatures(signatures_result: dict) -> list[dict]:
    if not signatures_result:
        return []
    return signatures_result if isinstance(signatures_result, list) else signatures_result.get("value", [])


def build_wallet_flow_features(largest_accounts_result: dict, signatures_result: dict, buy_sell_imbalance: float) -> dict:
    accounts = _extract_largest_accounts(largest_accounts_result)
    signatures = _extract_signatures(signatures_result)

    amounts: list[float] = []
    for account in accounts[:20]:
        amount_raw = account.get("amount", "0")
        try:
            amounts.append(float(amount_raw))
        except (TypeError, ValueError):
            amounts.append(0.0)

    total_amt = sum(amounts)
    top10_amt = sum(amounts[:10])
    top10_ratio = (top10_amt / total_amt) if total_amt > 0 else 1.0

    tx_activity = clamp01(len(signatures) / 50.0)
    concentration_penalty = clamp01(top10_ratio)
    buy_pressure = clamp01(buy_sell_imbalance)

    wallet_flow = clamp01(0.45 * tx_activity + 0.40 * buy_pressure + 0.15 * (1.0 - concentration_penalty))
    distribution_signal = clamp01(0.60 * concentration_penalty + 0.40 * (1.0 - buy_pressure))

    return {
        "wallet_flow": wallet_flow,
        "distribution_signal": distribution_signal,
        "top10_ratio_wallet": top10_ratio,
        "wallet_activity": tx_activity,
    }
