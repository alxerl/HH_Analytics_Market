from hh_market.transform.dedup import compare_publications


def test_exact_duplicate_wins_over_other_signals() -> None:
    result = compare_publications({"vacancy_id": "1"}, {"vacancy_id": "1"})
    assert result.is_duplicate and result.method == "exact_vacancy_id"


def test_missing_vacancy_ids_are_not_an_exact_duplicate() -> None:
    result = compare_publications({"vacancy_id": None}, {"vacancy_id": None})
    assert not result.is_duplicate


def test_near_duplicate_requires_same_employer() -> None:
    same = {"vacancy_id": "1", "employer_name": "Acme", "name": "Data Analyst"}
    similar = {"vacancy_id": "2", "employer_name": "Acme", "name": "Data Analyst Senior"}
    other = {"vacancy_id": "3", "employer_name": "Other", "name": "Data Analyst"}
    assert compare_publications(same, similar, threshold=0.5).is_duplicate
    assert not compare_publications(same, other).is_duplicate
