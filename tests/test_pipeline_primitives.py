import pytest

from hh_market.features.roles import classify_role
from hh_market.quality.checks import check_vacancies
from hh_market.transform.vacancy import canonicalize_vacancy


def test_canonical_vacancy_is_stable_and_cleans_description() -> None:
    payload = {
        "id": "7",
        "name": "Data Analyst",
        "description": "<p>SQL&nbsp;&amp; Python</p>",
        "employer": {"id": "1", "name": "Acme"},
        "area": {"id": "1", "name": "Москва"},
        "published_at": "2026-07-01T10:00:00+03:00",
    }
    record = canonicalize_vacancy(payload)
    assert record.description_text == "SQL & Python"
    assert record.content_hash == canonicalize_vacancy(payload).content_hash


def test_canonical_vacancy_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        canonicalize_vacancy({"id": "1", "name": ""})


def test_role_baseline_and_quality_check() -> None:
    assert classify_role("Product analyst").label == "product_analyst"
    record = canonicalize_vacancy({"id": "1", "name": "Data Analyst"})
    results = check_vacancies([record, record])
    assert not results[0].passed
    assert results[1].passed
