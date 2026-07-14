"""Deterministic exact and near-duplicate publication helpers."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from .clean_text import normalize_text


@dataclass(frozen=True)
class DuplicateDecision:
    is_duplicate: bool
    method: str
    similarity: float


def compare_publications(
    left: dict[str, str | None],
    right: dict[str, str | None],
    *,
    threshold: float = 0.92,
) -> DuplicateDecision:
    left_id = left.get("vacancy_id")
    right_id = right.get("vacancy_id")
    if left_id is not None and left_id == right_id:
        return DuplicateDecision(True, "exact_vacancy_id", 1.0)
    employer_left = normalize_text(left.get("employer_name"))
    employer_right = normalize_text(right.get("employer_name"))
    title_left = normalize_text(left.get("name")) or ""
    title_right = normalize_text(right.get("name")) or ""
    if employer_left != employer_right or not title_left or not title_right:
        return DuplicateDecision(False, "not_comparable", 0.0)
    similarity = SequenceMatcher(None, title_left, title_right).ratio()
    return DuplicateDecision(similarity >= threshold, "employer_title_similarity", similarity)
