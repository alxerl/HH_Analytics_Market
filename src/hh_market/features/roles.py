"""High-precision baseline role classifier with an explicit fallback."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RolePrediction:
    label: str
    confidence: float
    decision_path: str


_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("data_scientist", ("data scientist", "дата-сайентист", "machine learning")),
    ("product_analyst", ("product analyst", "продуктов", "продуктов\u044bй аналитик")),
    ("bi_analyst", ("bi analyst", "business intelligence", "power bi")),
    ("system_analyst", ("system analyst", "системн\u044bй аналитик")),
    ("business_analyst", ("business analyst", "бизнес-аналитик")),
    ("marketing_analyst", ("marketing analyst", "маркетингов")),
    ("financial_analyst", ("financial analyst", "финансов\u044bй аналитик")),
    ("data_analyst", ("data analyst", "аналитик данных", "data analytics")),
)


def classify_role(title: str | None, description: str | None = None) -> RolePrediction:
    text = " ".join(value for value in (title, description) if value).casefold()
    for label, markers in _RULES:
        if any(marker in text for marker in markers):
            return RolePrediction(label, 0.95, f"rule:{label}")
    if "аналитик" in text or "analyst" in text:
        return RolePrediction("other_analytics", 0.6, "rule:generic_analyst")
    return RolePrediction("unclear", 0.0, "rule:no_match")
