from app.clients.base_client import BaseHttpClient


class DexScreenerClient(BaseHttpClient):
    async def search_pairs(self, query: str) -> list[dict]:
        payload = await self.get("latest/dex/search", params={"q": query})
        return payload.get("pairs", [])
