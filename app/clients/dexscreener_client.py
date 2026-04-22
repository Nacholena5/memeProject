from app.clients.base_client import BaseHttpClient


class DexScreenerClient(BaseHttpClient):
    async def search_pairs(self, query: str) -> list[dict]:
        payload = await self.get("latest/dex/search", params={"q": query})
        return payload.get("pairs", [])

    async def token_pairs(self, token_address: str) -> list[dict]:
        payload = await self.get(f"latest/dex/tokens/{token_address}")
        return payload.get("pairs", [])
