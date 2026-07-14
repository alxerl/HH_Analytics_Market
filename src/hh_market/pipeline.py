"""File-based end-to-end operations used before the PostgreSQL loader is enabled."""

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .features.roles import classify_role
from .features.skills import extract_skills
from .quality.checks import check_vacancies
from .recommendation.profile import CandidateProfile
from .recommendation.scoring import score_vacancy
from .transform.vacancy import CanonicalVacancy, canonicalize_vacancy


def transform_snapshot(
    raw_root: Path, snapshot_date: date, skills_path: Path, reports_root: Path
) -> dict[str, int]:
    dictionary, version = _load_skill_dictionary(skills_path)
    records: list[dict[str, Any]] = []
    canonical_records: list[CanonicalVacancy] = []
    for path in sorted((raw_root / snapshot_date.isoformat()).rglob("page-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                continue
            canonical = canonicalize_vacancy(item)
            canonical_records.append(canonical)
            role = classify_role(canonical.name_raw, canonical.description_text)
            skills = extract_skills(canonical.description_text, dictionary, version)
            record = asdict(canonical)
            record["published_at"] = (
                canonical.published_at.isoformat() if canonical.published_at else None
            )
            record["role"] = asdict(role)
            record["skills"] = [asdict(skill) for skill in skills]
            records.append(record)
    quality = check_vacancies(canonical_records)
    output = reports_root / f"transformed-{snapshot_date.isoformat()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "snapshot_date": snapshot_date.isoformat(),
                "records": records,
                "quality": [asdict(item) for item in quality],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "records": len(records),
        "quality_failures": sum(not result.passed for result in quality),
    }


def _load_skill_dictionary(path: Path) -> tuple[dict[str, list[str]], str]:
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), dict):
        raise ValueError("Skill dictionary must contain a skills object")
    skills = payload["skills"]
    aliases_are_lists = all(
        isinstance(name, str) and isinstance(aliases, list) for name, aliases in skills.items()
    )
    if not aliases_are_lists:
        raise ValueError("Skill aliases must be lists")
    return skills, str(payload.get("version", "unknown"))


def recommend_from_report(
    reports_root: Path, snapshot_date: date, profile: CandidateProfile, top: int
) -> list[dict[str, Any]]:
    source = reports_root / f"transformed-{snapshot_date.isoformat()}.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    ranked: list[dict[str, Any]] = []
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        if record.get("employer_name") in profile.excluded_employers:
            continue
        role = record.get("role", {})
        role_label = role.get("label") if isinstance(role, dict) else None
        skills = record.get("skills", [])
        vacancy_skills = {
            item["canonical_name"]
            for item in skills
            if isinstance(item, dict) and "canonical_name" in item
        }
        result = score_vacancy(
            profile.current_skills | profile.preferred_skills,
            vacancy_skills,
            role_match=role_label in profile.target_roles,
        )
        ranked.append(
            {
                "vacancy_id": record["vacancy_id"],
                "name": record["name_raw"],
                "score": result.score,
                "matched_skills": result.matched_skills,
                "missing_skills": result.missing_skills,
                "factors": result.factors,
            }
        )
    return sorted(ranked, key=lambda item: (-float(item["score"]), str(item["vacancy_id"])))[:top]
