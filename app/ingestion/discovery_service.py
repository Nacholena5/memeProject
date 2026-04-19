from datetime import datetime, timezone

from app.config import get_settings
from app.features.normalization import clamp01, ratio_capped


def _pair_age_hours(created_at_ms: int | None) -> float:
    if not created_at_ms:
        return 0.0
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return max(0.0, (now_ms - int(created_at_ms)) / (1000 * 60 * 60))


def build_market_snapshot(pair: dict) -> dict:
    liquidity_usd = float((pair.get("liquidity") or {}).get("usd") or 0.0)
    volume_1h = float((pair.get("volume") or {}).get("h1") or 0.0)
    buys_1h = float((pair.get("txns") or {}).get("h1", {}).get("buys") or 0.0)
    sells_1h = float((pair.get("txns") or {}).get("h1", {}).get("sells") or 0.0)

    spread_bps = float(pair.get("spreadBps") or 0.0)
    if spread_bps <= 0:
        spread_bps = 30.0

    return {
        "address": (pair.get("baseToken") or {}).get("address", ""),
        "symbol": (pair.get("baseToken") or {}).get("symbol", ""),
        "price_usd": float(pair.get("priceUsd") or 0.0),
        "liquidity_usd": liquidity_usd,
        "volume_1h": volume_1h,
        "buy_sell_imbalance": ratio_capped(buys_1h, max(sells_1h, 1.0), cap=4.0),
        "spread_bps": spread_bps,
        "pair_age_hours": _pair_age_hours(pair.get("pairCreatedAt")),
    }


def candidate_filter(snapshot: dict) -> bool:
    settings = get_settings()
    return (
        snapshot["liquidity_usd"] >= settings.min_liquidity_usd
        and snapshot["volume_1h"] >= settings.min_volume_1h_usd
        and snapshot["spread_bps"] <= settings.max_spread_bps
    )


def market_features(snapshot: dict) -> dict:
    liquidity_quality = clamp01(snapshot["liquidity_usd"] / 300_000)
    volume_acceleration = clamp01(snapshot["volume_1h"] / 200_000)

    return {
        "liquidity_quality": liquidity_quality,
        "volume_acceleration": volume_acceleration,
    }
