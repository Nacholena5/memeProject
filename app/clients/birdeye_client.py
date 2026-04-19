from app.clients.base_client import BaseHttpClient


class BirdeyeClient(BaseHttpClient):
    def __init__(self, base_url: str, api_key: str) -> None:
        headers = {"x-api-key": api_key, "x-chain": "solana"} if api_key else {}
        super().__init__(base_url=base_url, default_headers=headers)

    async def token_overview(self, address: str) -> dict:
        return await self.get("defi/token_overview", params={"address": address})

    async def ohlcv(self, address: str, interval: str = "15m", limit: int = 200) -> list[dict]:
        payload = await self.get(
            "defi/ohlcv",
            params={"address": address, "type": interval, "limit": limit},
        )
        return payload.get("data", {}).get("items", [])
