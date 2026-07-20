from hh_market.recommendation.scoring import score_vacancy


def test_matching_is_deterministic_and_explainable() -> None:
    result = score_vacancy({"python", "sql", "tableau"}, {"sql", "python"})
    assert result.score == 0.866667
    assert result.matched_skills == ("python", "sql")
    assert result.missing_skills == ("tableau",)
    assert result.factors["skills"] == 2 / 3
