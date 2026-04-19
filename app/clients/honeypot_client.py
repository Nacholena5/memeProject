from app.clients.base_client import BaseHttpClient


class HoneypotClient(BaseHttpClient):
    async def honeypot_status(self, address: str, chain: str = "solana") -> dict:
        return await self.get("v2/IsHoneypot", params={"address": address, "chain": chain})
