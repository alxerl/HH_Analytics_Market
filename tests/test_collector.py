from datetime import date
from pathlib import Path

from hh_market.config import SearchQuery
from hh_market.ingestion.collector import collect_queries


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def get(self, _path: str, params: dict[str, str | int]) -> dict[str, object]:
        page = int(params["page"])
        self.calls.append(page)
        return {"items": [{"id": str(page)}] if page == 0 else [], "pages": 2}


def test_collection_is_resumable_and_writes_manifest(tmp_path: Path) -> None:
    query = SearchQuery(id="data-analyst", text="data analyst", areas=[1], pages_cap=3)
    first_client = FakeClient()
    first = collect_queries(first_client, [query], date(2026, 7, 14), tmp_path, resume=False)
    assert first.pages_collected == 2
    assert first.items_collected == 1
    assert (tmp_path / "2026-07-14" / "manifest.json").is_file()

    resumed_client = FakeClient()
    resumed = collect_queries(resumed_client, [query], date(2026, 7, 14), tmp_path, resume=True)
    assert resumed.pages_collected == 0
    assert resumed.pages_skipped == 2
    assert resumed_client.calls == []
