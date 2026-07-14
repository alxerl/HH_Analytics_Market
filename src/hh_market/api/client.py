"""Small, testable HeadHunter API client with bounded retries."""

from collections.abc import Mapping
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class HHApiError(RuntimeError):
    """A non-retryable or exhausted HeadHunter API failure."""


class HHClient:
    def __init__(
        self,
        base_url: str = "https://api.hh.ru",
        timeout: float = 30,
        max_retries: int = 4,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"User-Agent": "hh-analytics-market/0.1 (+https://github.com/)"},
            transport=transport,
        )
        self._attempts = max_retries + 1

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HHClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self._request(path, params)
        except (httpx.HTTPError, HHApiError) as exc:
            raise HHApiError(str(exc)) from exc
        if response.status_code >= 400:
            raise HHApiError(f"HH API returned HTTP {response.status_code} for {path}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise HHApiError("HH API returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise HHApiError("HH API response must be a JSON object")
        return payload

    def _request(self, path: str, params: Mapping[str, Any] | None) -> httpx.Response:
        @retry(
            retry=retry_if_exception_type((httpx.TransportError, _RetryableStatus)),
            stop=stop_after_attempt(self._attempts),
            wait=wait_exponential_jitter(initial=0.5, max=8),
            reraise=True,
        )
        def send() -> httpx.Response:
            response = self._client.get(path, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                raise _RetryableStatus(response)
            return response

        return send()


class _RetryableStatus(Exception):
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"retryable HTTP {response.status_code}")
