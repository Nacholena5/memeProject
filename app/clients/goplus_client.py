from app.clients.base_client import BaseHttpClient


class GoPlusClient(BaseHttpClient):
    async def token_security(self, chain_id: str, address: str) -> dict:
        payload = await self.get("api/v1/token_security", params={"chain_id": chain_id, "contract_addresses": address})
        result = payload.get("result", {})
        return result.get(address.lower(), {}) or result.get(address, {})
