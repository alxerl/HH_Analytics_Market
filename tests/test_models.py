from pathlib import Path

from hh_market.models.hybrid import predict_hybrid
from hh_market.models.train import train_role_model


def test_train_writes_model_and_model_card(tmp_path: Path) -> None:
    result = train_role_model(Path("data/labeling/gold_labels.csv"), tmp_path, "test-v1")
    assert result.model_path.is_file()
    assert (tmp_path / "role-test-v1.model-card.json").is_file()
    prediction = predict_hybrid("Unknown", "ML statistics Python", result.model_path, threshold=0)
    assert prediction.label


def test_hybrid_uses_high_precision_rule_without_model(tmp_path: Path) -> None:
    result = predict_hybrid("Product Analyst", None, tmp_path / "unused.joblib")
    assert result.label == "product_analyst"
    assert result.decision_path == "rule:product_analyst"
