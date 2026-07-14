"""Reproducible held-out model evaluation from a labeled CSV."""

import csv
from pathlib import Path

import joblib
from sklearn.metrics import f1_score


def evaluate_role_model(model_path: Path, dataset_path: Path) -> float:
    rows = list(csv.DictReader(dataset_path.open(encoding="utf-8", newline="")))
    model = joblib.load(model_path)
    texts = [f"{row['title']} {row['description']}" for row in rows]
    labels = [row["label"] for row in rows]
    return float(f1_score(labels, model.predict(texts), average="macro", zero_division=0))
