"""TF-IDF Logistic Regression training with grouped holdout and model card."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline


@dataclass(frozen=True)
class TrainingResult:
    model_path: Path
    model_version: str
    macro_f1: float
    train_rows: int
    test_rows: int


def train_role_model(dataset_path: Path, models_root: Path, model_version: str) -> TrainingResult:
    rows = list(csv.DictReader(dataset_path.open(encoding="utf-8", newline="")))
    if len(rows) < 4 or len({row["label"] for row in rows}) < 2:
        raise ValueError("Dataset must contain at least four rows and two labels")
    texts = [f"{row['title']} {row['description']}" for row in rows]
    labels = [row["label"] for row in rows]
    groups = [row.get("group_id") or row["vacancy_id"] for row in rows]
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_indices, test_indices = next(splitter.split(texts, labels, groups))
    pipeline = Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                        ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1)),
                    ]
                ),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            ),
        ]
    )
    train_texts = [texts[index] for index in train_indices]
    train_labels = [labels[index] for index in train_indices]
    test_texts = [texts[index] for index in test_indices]
    test_labels = [labels[index] for index in test_indices]
    pipeline.fit(train_texts, train_labels)
    predictions = pipeline.predict(test_texts)
    macro_f1 = float(f1_score(test_labels, predictions, average="macro", zero_division=0))
    models_root.mkdir(parents=True, exist_ok=True)
    model_path = models_root / f"role-{model_version}.joblib"
    joblib.dump(pipeline, model_path)
    card = {
        "model_version": model_version,
        "target": "role",
        "algorithm": "TF-IDF word/char + Logistic Regression",
        "dataset": str(dataset_path),
        "split": "GroupShuffleSplit(random_state=42)",
        "macro_f1": macro_f1,
        "classification_report": classification_report(test_labels, predictions, zero_division=0),
        "limitations": "Synthetic smoke dataset; do not use metric as a production claim.",
    }
    (models_root / f"role-{model_version}.model-card.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return TrainingResult(
        model_path, model_version, macro_f1, len(train_indices), len(test_indices)
    )
