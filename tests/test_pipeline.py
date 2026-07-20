import json
from datetime import date
from pathlib import Path

from hh_market.pipeline import transform_snapshot


def test_transform_snapshot_builds_versioned_report(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "2026-07-14" / "query" / "1"
    raw.mkdir(parents=True)
    payload = {"items": [{"id": "1", "name": "Data Analyst", "description": "SQL and Python"}]}
    (raw / "page-0000.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    skills = tmp_path / "skills.yml"
    skills.write_text("version: '1'\nskills:\n  sql: []\n  python: []\n", encoding="utf-8")
    result = transform_snapshot(
        tmp_path / "raw", date(2026, 7, 14), skills, tmp_path / "reports"
    )
    report_path = tmp_path / "reports" / "transformed-2026-07-14.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result == {"records": 1, "quality_failures": 0}
    assert report["records"][0]["role"]["label"] == "data_analyst"
    assert [item["canonical_name"] for item in report["records"][0]["skills"]] == ["python", "sql"]
