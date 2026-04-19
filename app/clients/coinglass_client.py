from app.clients.base_client import BaseHttpClient


class CoinGlassClient(BaseHttpClient):
    def __init__(self, base_url: str, api_key: str) -> None:
        headers = {"CG-API-KEY": api_key} if api_key else {}
        super().__init__(base_url=base_url, default_headers=headers)

    async def funding_oi_snapshot(self, symbol: str = "SOL") -> dict:
        if not self._default_headers:
            return {}
        payload = await self.get("api/futures/fundingRate/ohlc-history", params={"symbol": symbol, "interval": "1h", "limit": 50})
        return payload
