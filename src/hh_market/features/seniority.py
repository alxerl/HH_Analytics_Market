"""Explainable seniority baseline."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SeniorityResult:
    bucket: str
    score: float
    explicit_experience: float
    title_signal: float
    responsibility_signal: float
    explanation: dict[str, str]


def classify_seniority(title: str | None, description: str | None) -> SeniorityResult:
    title_text = (title or "").casefold()
    body = (description or "").casefold()
    explicit = 0.0
    years = re.search(r"(\d+)\s*(?:-|до\s*)?(\d+)?\s*(?:год|лет|years?)", body)
    if years:
        explicit = min(float(years.group(1)) / 3, 1.0)
    title_signal = 1.0 if any(word in title_text for word in ("senior", "lead", "ведущ")) else 0.0
    title_signal = (
        -1.0
        if any(word in title_text for word in ("junior", "стажер", "стажёр"))
        else title_signal
    )
    responsibility = (
        1.0 if any(word in body for word in ("руководить", "lead", "стратеги")) else 0.0
    )
    score = max(-1.0, min(1.0, explicit + title_signal * 0.7 + responsibility * 0.3))
    bucket = "junior" if score < 0 else "middle" if score < 0.8 else "senior"
    return SeniorityResult(
        bucket, score, explicit, title_signal, responsibility, {"rule": "baseline-v1"}
    )
