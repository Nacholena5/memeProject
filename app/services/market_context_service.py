from __future__ import annotations

from datetime import datetime, timezone

from app.clients.dexscreener_client import DexScreenerClient
from app.config import get_settings


class MarketContextService:
    def __init__(self) -> None:
        settings = get_settings()
        self._dex = DexScreenerClient(settings.dexscreener_base_url)

    @staticmethod
    def _trend_from_change(change_pct: float) -> str:
        if change_pct > 1.5:
            return "alcista"
        if change_pct < -1.5:
            return "bajista"
        return "neutral"

    @staticmethod
    def _liquidity_bucket(liquidity_usd: float) -> str:
        if liquidity_usd > 25_000_000:
            return "alta"
        if liquidity_usd > 7_500_000:
            return "media"
        return "baja"

    @staticmethod
    def _avg_change(pairs: list[dict]) -> float:
        if not pairs:
            return 0.0
        changes = []
        for pair in pairs[:10]:
            change = (pair.get("priceChange") or {}).get("h24")
            if change is None:
                continue
            try:
                changes.append(float(change))
            except (TypeError, ValueError):
                continue
        return (sum(changes) / len(changes)) if changes else 0.0

    @staticmethod
    def _sum_liquidity(pairs: list[dict]) -> float:
        total = 0.0
        for pair in pairs[:20]:
            liq = (pair.get("liquidity") or {}).get("usd")
            try:
                total += float(liq or 0.0)
            except (TypeError, ValueError):
                continue
        return total

    async def compute_context(self) -> dict:
        now = datetime.now(timezone.utc)
        stale_sources: list[str] = []

        async def safe_search(query: str, source_key: str) -> list[dict]:
            try:
                rows = await self._dex.search_pairs(query)
                return rows if isinstance(rows, list) else []
            except Exception:
                stale_sources.append(source_key)
                return []

        btc_pairs = await safe_search("BTC USDC", "dex:btc")
        sol_pairs = await safe_search("SOL USDC", "dex:sol")
        meme_pairs = await safe_search("solana meme", "dex:meme")

        btc_change = self._avg_change(btc_pairs)
        sol_change = self._avg_change(sol_pairs)
        meme_change = self._avg_change(meme_pairs)

        total_liquidity = self._sum_liquidity(meme_pairs)

        data_points = sum(1 for arr in [btc_pairs, sol_pairs, meme_pairs] if len(arr) > 0)
        confidence = 0.35 + (data_points * 0.2)
        confidence = max(0.0, min(0.95, confidence))

        degraded_reasons: list[str] = []
        if not btc_pairs:
            degraded_reasons.append("sin datos BTC")
        if not sol_pairs:
            degraded_reasons.append("sin datos SOL")
        if not meme_pairs:
            degraded_reasons.append("sin universo meme")

        if meme_change > 4:
            meme_regime = "caliente"
        elif meme_change < -2:
            meme_regime = "frío"
        else:
            meme_regime = "normal"

        status = "ok" if len(degraded_reasons) == 0 else "degradado"
        source_freshness = "tiempo real" if len(stale_sources) == 0 else "parcial"

        return {
            "status": status,
            "btc_trend": self._trend_from_change(btc_change),
            "sol_trend": self._trend_from_change(sol_change),
            "meme_regime": meme_regime,
            "market_liquidity": self._liquidity_bucket(total_liquidity),
            "source_freshness": source_freshness,
            "calculated_at": now.isoformat(),
            "confidence": round(confidence, 3),
            "degraded_reasons": degraded_reasons,
            "stale_sources": stale_sources,
            "calc_method": {
                "btc_trend": "promedio priceChange.h24 de pares BTC/USDC en DexScreener",
                "sol_trend": "promedio priceChange.h24 de pares SOL/USDC en DexScreener",
                "meme_regime": "promedio h24 del universo de búsqueda 'solana meme'",
                "market_liquidity": "suma de liquidez USD en top pares del universo meme",
            },
        }
