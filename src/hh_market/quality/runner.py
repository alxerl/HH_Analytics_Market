"""Database data-quality runner with persisted JSON and Markdown reports."""

import json
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path

import psycopg

from .checks import QualityResult

_SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def run_database_quality(
    database_url: str,
    run_id: uuid.UUID,
    snapshot_date: date,
    reports_root: Path,
) -> list[QualityResult]:
    checks = (
        ("snapshot_orphans", "critical", """
            SELECT count(*) FROM raw.vacancy_snapshots snapshot
            LEFT JOIN raw.api_requests request ON request.request_id = snapshot.source_request_id
            WHERE request.request_id IS NULL
        """, 0),
        ("active_current_duplicates", "critical", """
            SELECT count(*) FROM (
              SELECT vacancy_id FROM core.publications
              WHERE snapshot_date = %s AND is_active AND is_representative
              GROUP BY vacancy_id HAVING count(*) > 1
            ) duplicates
        """, 0),
        ("invalid_salary_bounds", "critical", """
            SELECT count(*) FROM core.salary_offers
            WHERE from_rub < 0 OR to_rub < 0
              OR (from_rub IS NOT NULL AND to_rub IS NOT NULL AND from_rub > to_rub)
        """, 0),
        ("duplicate_cluster_single_representative", "critical", """
            SELECT count(*) FROM (
              SELECT cluster_id
              FROM core.duplicate_cluster_members
              GROUP BY cluster_id
              HAVING count(*) FILTER (WHERE is_representative) <> 1
            ) invalid_clusters
        """, 0),
        ("prediction_version_present", "critical", """
            SELECT count(*) FROM ml.predictions
            WHERE model_version IS NULL AND rules_version IS NULL
        """, 0),
        ("vacancy_skill_orphans", "critical", """
            SELECT count(*) FROM core.vacancy_skills vacancy_skill
            LEFT JOIN core.skills skill ON skill.skill_id = vacancy_skill.skill_id
            WHERE skill.skill_id IS NULL
        """, 0),
        ("unknown_role_share", "warning", """
            SELECT count(*) FROM ml.predictions
            WHERE target = 'role' AND predicted_class = 'unclear'
        """, None),
    )
    results: list[QualityResult] = []
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ops.pipeline_runs (
                  run_id, pipeline_name, snapshot_date, status, code_version, config_hash
                )
                VALUES (%s, 'quality', %s, 'started', '0.1.0', 'local')
                ON CONFLICT (run_id) DO NOTHING
                """,
                (run_id, snapshot_date),
            )
            for name, severity, statement, expected in checks:
                parameters = (snapshot_date,) if "%s" in statement else ()
                row = cursor.execute(statement, parameters).fetchone()
                assert row is not None
                observed = int(row[0])
                passed = True if expected is None else observed <= expected
                result = QualityResult(name, severity, passed, observed, expected or 0)
                results.append(result)
                cursor.execute(
                    """
                    INSERT INTO ops.quality_results (
                      run_id, check_name, severity, passed, observed, expected
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (run_id, name, severity, passed, observed, expected),
                )
            critical_failure = any(
                not item.passed and item.severity == "critical" for item in results
            )
            status = "failed" if critical_failure else "succeeded"
            cursor.execute(
                """
                UPDATE ops.pipeline_runs SET status = %s, finished_at = now()
                WHERE run_id = %s
                """,
                (status, run_id),
            )
        connection.commit()
    _write_reports(reports_root, run_id, results)
    return results


def should_fail(results: list[QualityResult], fail_on: str) -> bool:
    threshold = _SEVERITY_ORDER[fail_on]
    return any(not item.passed and _SEVERITY_ORDER[item.severity] >= threshold for item in results)


def _write_reports(reports_root: Path, run_id: uuid.UUID, results: list[QualityResult]) -> None:
    reports_root.mkdir(parents=True, exist_ok=True)
    payload = [asdict(item) for item in results]
    (reports_root / f"quality-{run_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Data quality report",
        "",
        "| Check | Severity | Passed | Observed | Expected |",
        "|---|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {item.name} | {item.severity} | {item.passed} | {item.observed} | {item.expected} |"
        for item in results
    )
    (reports_root / f"quality-{run_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
