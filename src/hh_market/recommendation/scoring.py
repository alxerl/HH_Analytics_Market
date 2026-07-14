"""Explainable profile-to-vacancy scoring."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    score: float
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    factors: dict[str, float]


def score_vacancy(
    profile_skills: set[str],
    vacancy_skills: set[str],
    *,
    role_match: bool = True,
    seniority_match: bool = True,
    salary_match: bool = True,
) -> MatchResult:
    matched = tuple(sorted(profile_skills & vacancy_skills))
    missing = tuple(sorted(profile_skills - vacancy_skills))
    skill_score = len(matched) / len(profile_skills) if profile_skills else 0.0
    factors = {
        "skills": skill_score,
        "role": 1.0 if role_match else 0.0,
        "seniority": 1.0 if seniority_match else 0.0,
        "salary": 1.0 if salary_match else 0.0,
    }
    score = (
        factors["skills"] * 0.6
        + factors["role"] * 0.2
        + factors["seniority"] * 0.1
        + factors["salary"] * 0.1
    )
    return MatchResult(round(score, 6), matched, missing, factors)
