import json
from datetime import date

import httpx

from hh_market.api.client import HHClient
from hh_market.ingestion.raw_store import RawStore


def test_client_retries_429_then_returns_json() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429 if calls == 1 else 200, json={"items": []})

    with HHClient(transport=httpx.MockTransport(handler), max_retries=2) as client:
        assert client.get("/vacancies") == {"items": []}
    assert calls == 2


def test_raw_store_is_canonical_and_idempotent(tmp_path) -> None:
    store = RawStore(tmp_path)
    payload = {"b": 2, "a": "тест"}
    first = store.write_json(date(2026, 7, 14), "data-analyst", 1, 0, payload)
    second = store.write_json(date(2026, 7, 14), "data-analyst", 1, 0, payload)
    assert first == second
    assert json.loads(first.path.read_text(encoding="utf-8")) == payload
