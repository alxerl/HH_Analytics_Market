from hh_market.features.seniority import classify_seniority
from hh_market.features.skills import extract_skills


def test_skills_use_boundaries_and_aliases() -> None:
    matches = extract_skills(
        "Python, SQL and Power BI. R is optional.",
        {"python": ["py"], "sql": [], "r": []},
        "1.0.0",
    )
    assert [item.canonical_name for item in matches] == ["python", "r", "sql"]
    assert not extract_skills("pyramid", {"py": []}, "1.0.0")


def test_seniority_returns_explanation_and_bucket() -> None:
    result = classify_seniority("Senior Data Analyst", "5 years experience; lead strategy")
    assert result.bucket == "senior"
    assert result.explanation["rule"] == "baseline-v1"
