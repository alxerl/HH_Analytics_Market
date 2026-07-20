"""Persist hybrid model role predictions with complete traceability."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from ..models.hybrid import predict_hybrid


def persist_hybrid_predictions(
    database_url: str, model_path: Path, model_version: str
) -> dict[str, int]:
    artifact_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    card_path = model_path.with_suffix(".model-card.json")
    metrics = json.loads(card_path.read_text(encoding="utf-8")) if card_path.is_file() else {}
    count = 0
    with psycopg.connect(database_url) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO ml.model_versions (
                  model_version, target, algorithm, trained_at, dataset_version, feature_hash,
                  metrics, artifact_path, status
                ) VALUES (
                  %s, 'role', 'hybrid rules + TF-IDF Logistic Regression', %s,
                  'gold-v1', %s, %s, %s, 'champion'
                )
                ON CONFLICT (model_version) DO UPDATE SET
                  feature_hash = EXCLUDED.feature_hash,
                  artifact_path = EXCLUDED.artifact_path,
                  status = 'champion'
                """,
                (
                    model_version,
                    datetime.now(timezone.utc),
                    artifact_hash,
                    json.dumps(metrics),
                    str(model_path),
                ),
            )
            rows = cursor.execute(
                "SELECT vacancy_id, name_raw, description_text FROM core.vacancies"
            ).fetchall()
            for row in rows:
                prediction = predict_hybrid(row["name_raw"], row["description_text"], model_path)
                cursor.execute(
                    """
                    INSERT INTO ml.predictions (
                      vacancy_id, target, predicted_class, confidence, class_probabilities,
                      model_version, rules_version, decision_path
                    ) VALUES (%s, 'role', %s, %s, %s, %s, 'baseline-v1', %s)
                    ON CONFLICT (vacancy_id, target, model_version, rules_version) DO UPDATE SET
                      predicted_class = EXCLUDED.predicted_class, confidence = EXCLUDED.confidence,
                      class_probabilities = EXCLUDED.class_probabilities,
                      decision_path = EXCLUDED.decision_path, predicted_at = now()
                    """,
                    (
                        row["vacancy_id"],
                        prediction.label,
                        prediction.confidence,
                        json.dumps({prediction.label: prediction.confidence}),
                        model_version,
                        prediction.decision_path,
                    ),
                )
                count += 1
        connection.commit()
    return {"hybrid_predictions": count}
