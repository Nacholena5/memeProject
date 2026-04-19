from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class BaseHttpClient:
    def __init__(self, base_url: str, default_headers: dict[str, str] | None = None, timeout: float = 12.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_headers = default_headers or {}
        self._timeout = timeout

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.5, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
    )
    async def get(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        merged_headers = {**self._default_headers, **(headers or {})}
        url = f"{self._base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=merged_headers)
            response.raise_for_status()
            return response.json()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.5, max=3),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
    )
    async def post(self, path: str, json_body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        merged_headers = {**self._default_headers, **(headers or {})}
        url = f"{self._base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=json_body, headers=merged_headers)
            response.raise_for_status()
            return response.json()
