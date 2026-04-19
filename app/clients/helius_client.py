from app.clients.base_client import BaseHttpClient


class HeliusClient(BaseHttpClient):
    def __init__(self, rpc_url: str, api_key: str) -> None:
        super().__init__(base_url=rpc_url.rstrip("/"))
        self._api_key = api_key

    async def _rpc(self, method: str, params: list) -> dict:
        if not self._api_key:
            return {}

        path = f"/?api-key={self._api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": "meme-research",
            "method": method,
            "params": params,
        }
        response = await self.post(path=path, json_body=payload)
        return response.get("result", {}) if isinstance(response, dict) else {}

    async def get_token_largest_accounts(self, mint_address: str) -> dict:
        return await self._rpc("getTokenLargestAccounts", [mint_address])

    async def get_signatures_for_address(self, address: str, limit: int = 50) -> dict:
        params = [address, {"limit": limit}]
        return await self._rpc("getSignaturesForAddress", params)
