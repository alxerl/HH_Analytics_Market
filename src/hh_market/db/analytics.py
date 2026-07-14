"""Persistence of deterministic analytical features and rule predictions."""

import json
from pathlib import Path
from typing import Any

import psycopg
import yaml

from ..features.roles import classify_role
from ..features.seniority import classify_seniority
from ..features.skills import extract_skills


def persist_rule_features(database_url: str, skills_path: Path) -> dict[str, int]:
    """Calculate and upsert baseline features for all canonical vacancies."""
    dictionary, dictionary_version = _read_skills(skills_path)
    predictions = seniority_scores = skill_matches = 0
    with psycopg.connect(database_url) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            rows = cursor.execute(
                "SELECT vacancy_id, name_raw, description_text FROM core.vacancies"
            ).fetchall()
            for row in rows:
                vacancy_id = row["vacancy_id"]
                role = classify_role(row["name_raw"], row["description_text"])
                cursor.execute(
                    """
                    INSERT INTO ml.predictions (
                      vacancy_id, target, predicted_class, confidence, class_probabilities,
                      rules_version, decision_path
                    ) VALUES (%s, 'role', %s, %s, %s, 'baseline-v1', %s)
                    ON CONFLICT (vacancy_id, target, model_version, rules_version) DO UPDATE SET
                      predicted_class = EXCLUDED.predicted_class, confidence = EXCLUDED.confidence,
                      class_probabilities = EXCLUDED.class_probabilities,
                      decision_path = EXCLUDED.decision_path, predicted_at = now()
                    """,
                    (
                        vacancy_id,
                        role.label,
                        role.confidence,
                        json.dumps({role.label: role.confidence}),
                        role.decision_path,
                    ),
                )
                predictions += 1
                seniority = classify_seniority(row["name_raw"], row["description_text"])
                cursor.execute(
                    """
                    INSERT INTO ml.seniority_scores (
                      vacancy_id, score, explicit_experience, title_signal, responsibility_signal,
                      bucket, rules_version, explanation
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'baseline-v1', %s)
                    ON CONFLICT (vacancy_id) DO UPDATE SET
                      score = EXCLUDED.score, explicit_experience = EXCLUDED.explicit_experience,
                      title_signal = EXCLUDED.title_signal,
                      responsibility_signal = EXCLUDED.responsibility_signal,
                      bucket = EXCLUDED.bucket, rules_version = EXCLUDED.rules_version,
                      explanation = EXCLUDED.explanation
                    """,
                    (
                        vacancy_id,
                        seniority.score,
                        seniority.explicit_experience,
                        seniority.title_signal,
                        seniority.responsibility_signal,
                        seniority.bucket,
                        json.dumps(seniority.explanation),
                    ),
                )
                seniority_scores += 1
                matches = extract_skills(row["description_text"], dictionary, dictionary_version)
                for match in matches:
                    skill_id = _upsert_skill(cursor, match.canonical_name, dictionary_version)
                    cursor.execute(
                        """
                        INSERT INTO core.vacancy_skills (
                          vacancy_id, skill_id, source, match_text, confidence, extractor_version
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (vacancy_id, skill_id, extractor_version) DO UPDATE SET
                          source = EXCLUDED.source, match_text = EXCLUDED.match_text,
                          confidence = EXCLUDED.confidence
                        """,
                        (
                            vacancy_id,
                            skill_id,
                            match.source,
                            match.match_text,
                            match.confidence,
                            dictionary_version,
                        ),
                    )
                    skill_matches += 1
        connection.commit()
    return {
        "predictions": predictions,
        "seniority_scores": seniority_scores,
        "skill_matches": skill_matches,
    }


def _upsert_skill(cursor: psycopg.Cursor[Any], canonical_name: str, version: str) -> int:
    row = cursor.execute(
        """
        INSERT INTO core.skills (canonical_name, dictionary_version)
        VALUES (%s, %s)
        ON CONFLICT (canonical_name) DO UPDATE SET dictionary_version = EXCLUDED.dictionary_version
        RETURNING skill_id
        """,
        (canonical_name, version),
    ).fetchone()
    assert row is not None
    return int(row[0])


def _read_skills(path: Path) -> tuple[dict[str, list[str]], str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), dict):
        raise ValueError("Skill dictionary must contain a skills object")
    return payload["skills"], str(payload.get("version", "unknown"))
