from __future__ import annotations

from typing import Any

from app.clients.base_client import BaseHttpClient


class PolymarketClient(BaseHttpClient):
    async def search_markets(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        try:
            payload = await self.get("/markets", params={"search": query, "limit": limit})
            if isinstance(payload, dict):
                if "markets" in payload and isinstance(payload["markets"], list):
                    return payload["markets"]
                if "data" in payload and isinstance(payload["data"], list):
                    return payload["data"]
                if "results" in payload and isinstance(payload["results"], list):
                    return payload["results"]
            if isinstance(payload, list):
                return payload
        except Exception:
            return []

        return []

    async def market_detail(self, market_id: str) -> dict[str, Any]:
        try:
            payload = await self.get(f"/markets/{market_id}")
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}
