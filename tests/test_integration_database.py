import json
import os
import uuid
from datetime import date
from pathlib import Path

import pytest

from hh_market.db.analytics import persist_rule_features
from hh_market.db.loaders import load_core_snapshot, load_raw_snapshot
from hh_market.db.marts import build_marts
from hh_market.db.matching import recommend_from_database
from hh_market.db.migrations import apply_migrations
from hh_market.quality.runner import run_database_quality
from hh_market.recommendation.profile import CandidateProfile

DATABASE_URL = os.getenv("HH_MARKET_INTEGRATION_DB_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="PostgreSQL integration database is not configured"
)


def test_database_end_to_end(tmp_path: Path) -> None:
    assert DATABASE_URL is not None
    migrations = Path("migrations")
    apply_migrations(DATABASE_URL, migrations)
    snapshot_date = date(2026, 7, 14)
    raw_page = tmp_path / "raw" / snapshot_date.isoformat() / "data-analyst" / "1"
    raw_page.mkdir(parents=True)
    raw_page.joinpath("page-0000.json").write_text(
        json.dumps(
            {
                "found": 1,
                "items": [
                    {
                        "id": "integration-1",
                        "name": "Data Analyst",
                        "description": "<p>SQL and Python</p>",
                        "employer": {"id": "employer-1", "name": "Acme"},
                        "area": {"id": "1", "name": "Москва"},
                        "salary": {"from": 100000, "to": 150000, "currency": "RUR", "gross": False},
                        "published_at": "2026-07-01T10:00:00+03:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    run_id = uuid.uuid4()
    raw_summary = load_raw_snapshot(DATABASE_URL, tmp_path / "raw", snapshot_date, run_id)
    assert raw_summary["vacancy_snapshots"] == 1
    assert load_core_snapshot(DATABASE_URL, snapshot_date, run_id)["vacancies"] == 1
    assert persist_rule_features(DATABASE_URL, Path("config/skills.yml"))["predictions"] >= 1
    assert build_marts(DATABASE_URL)["vacancy_current"] >= 1
    results = run_database_quality(DATABASE_URL, uuid.uuid4(), snapshot_date, tmp_path / "reports")
    assert all(item.passed for item in results if item.severity == "critical")
    profile = CandidateProfile(target_roles=["data_analyst"], current_skills={"sql", "python"})
    recommendations = recommend_from_database(
        DATABASE_URL, snapshot_date, profile, 5, tmp_path / "reports"
    )
    assert recommendations[0]["vacancy_id"] == "integration-1"
