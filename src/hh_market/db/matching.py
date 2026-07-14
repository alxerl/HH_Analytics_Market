"""Deterministic profile matching directly against the stable mart grain."""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

from ..recommendation.profile import CandidateProfile
from ..recommendation.scoring import score_vacancy


def recommend_from_database(
    database_url: str, as_of_date: date, profile: CandidateProfile, top: int, reports_root: Path
) -> list[dict[str, Any]]:
    """Rank representative active vacancies and save a reproducible output artifact."""
    with psycopg.connect(database_url) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            rows = cursor.execute(
                """
                SELECT current.*, employer.name AS employer_name,
                       coalesce(
                         array_agg(skill.canonical_name)
                           FILTER (WHERE skill.skill_id IS NOT NULL),
                         '{}'
                       ) AS skills
                FROM mart.vacancy_current AS current
                JOIN core.vacancies AS vacancy ON vacancy.vacancy_id = current.vacancy_id
                LEFT JOIN core.employers AS employer ON employer.employer_id = vacancy.employer_id
                LEFT JOIN core.vacancy_skills AS vacancy_skill
                  ON vacancy_skill.vacancy_id = current.vacancy_id
                LEFT JOIN core.skills AS skill ON skill.skill_id = vacancy_skill.skill_id
                WHERE current.as_of_date = %s
                GROUP BY current.as_of_date, current.vacancy_id, current.name_raw,
                         current.area_id, current.area_name, current.published_at,
                         current.alternate_url, current.is_active, current.is_representative,
                         current.role, current.seniority, current.midpoint_rub, employer.name
                """,
                (as_of_date,),
            ).fetchall()
    ranked = [_score_row(row, profile) for row in rows if _eligible(row, profile)]
    ranked.sort(
        key=lambda item: (-float(item["score"]), item["published_at"] or "", item["vacancy_id"])
    )
    result = ranked[:top]
    reports_root.mkdir(parents=True, exist_ok=True)
    output = reports_root / f"recommendations-{as_of_date.isoformat()}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _eligible(row: dict[str, Any], profile: CandidateProfile) -> bool:
    employer = str(row.get("employer_name") or "").casefold()
    return employer not in {name.casefold() for name in profile.excluded_employers}


def _score_row(row: dict[str, Any], profile: CandidateProfile) -> dict[str, Any]:
    published_at = row.get("published_at")
    age_days = (datetime.now(timezone.utc) - published_at).days if published_at else 30
    score = score_vacancy(
        profile.current_skills | profile.preferred_skills,
        set(row["skills"]),
        role_match=row.get("role") in profile.target_roles,
        seniority_match=(
            profile.target_seniority is None or row.get("seniority") == profile.target_seniority
        ),
        location_match=not profile.locations or row.get("area_id") in profile.locations,
        salary_match=row.get("midpoint_rub") is None
        or profile.salary_floor_rub is None
        or row["midpoint_rub"] >= profile.salary_floor_rub,
        freshness=max(0.0, 1 - age_days / 30),
    )
    return {
        "vacancy_id": row["vacancy_id"],
        "name": row["name_raw"],
        "published_at": published_at.isoformat() if published_at else None,
        "score": score.score,
        "matched_skills": score.matched_skills,
        "missing_skills": score.missing_skills,
        "factors": score.factors,
    }
