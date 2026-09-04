from datetime import date
from pathlib import Path

import httpx
import pytest

from hh_market.api.client import HHApiError, HHClient
from hh_market.config import SearchQuery
from hh_market.features.skills import extract_skills
from hh_market.ingestion.collector import collect_queries
from hh_market.pipeline import transform_snapshot


def test_skill_alias_is_used_when_canonical_name_is_absent() -> None:
    matches = extract_skills("Power BI and PostgreSQL", {
        "power_bi": ["power bi"], "sql": ["postgresql"]}, "test")
    assert [item.canonical_name for item in matches] == ["power_bi", "sql"]


def test_denied_access_is_not_retried_and_has_diagnostic() -> None:
    calls = []

    def response(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer test-secret"
        return httpx.Response(403, json={"errors": [{"type": "forbidden"}], "request_id": "r1"})

    with HHClient(transport=httpx.MockTransport(response), access_token="test-secret") as client:
        with pytest.raises(HHApiError, match="request_id=r1") as error:
            client.get("/vacancies")
    assert "test-secret" not in str(error.value)
    assert len(calls) == 1


def test_details_are_loaded_once_and_transform_deduplicates(tmp_path: Path) -> None:
    calls = []

    def response(request):
        calls.append(request.url.path)
        if request.url.path == "/vacancies":
            return httpx.Response(200, json={"items": [{"id": "1"}], "pages": 1})
        return httpx.Response(200, json={"id": "1", "name": "Data Analyst",
                                        "description": "SQL Python"})

    queries = [SearchQuery(id=q, text=q, areas=[1]) for q in ["one", "two"]]
    with HHClient(transport=httpx.MockTransport(response)) as client:
        collect_queries(client, queries, date(2026, 9, 4), tmp_path / "raw",
                        resume=False, include_details=True)
    assert calls.count("/vacancies/1") == 1
    result = transform_snapshot(tmp_path / "raw", date(2026, 9, 4),
                                Path("config/skills.yml"), tmp_path / "reports")
    assert result["records"] == 1


def test_missing_collection_cannot_produce_successful_empty_report(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No collected pages"):
        transform_snapshot(tmp_path, date(2026, 9, 4), Path("config/skills.yml"), tmp_path)
