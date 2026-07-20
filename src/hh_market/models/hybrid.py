"""Rules-first role inference with probability threshold fallback."""

from pathlib import Path

import joblib

from ..features.roles import RolePrediction, classify_role


def predict_hybrid(
    title: str | None, description: str | None, model_path: Path, threshold: float = 0.55
) -> RolePrediction:
    rule = classify_role(title, description)
    if rule.confidence >= 0.9:
        return rule
    model = joblib.load(model_path)
    text = f"{title or ''} {description or ''}"
    probabilities = model.predict_proba([text])[0]
    index = int(probabilities.argmax())
    confidence = float(probabilities[index])
    if confidence < threshold:
        return RolePrediction("unclear", confidence, "hybrid:ml_below_threshold")
    return RolePrediction(str(model.classes_[index]), confidence, "hybrid:ml")
