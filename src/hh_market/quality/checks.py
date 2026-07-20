"""Small deterministic checks suitable for raw/core pipeline gates."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from ..transform.vacancy import CanonicalVacancy


@dataclass(frozen=True)
class QualityResult:
    name: str
    severity: str
    passed: bool
    observed: int
    expected: int


def check_vacancies(records: Iterable[CanonicalVacancy]) -> list[QualityResult]:
    rows = list(records)
    ids = [record.vacancy_id for record in rows]
    invalid_dates = sum(
        record.published_at is not None and record.published_at > datetime.now(timezone.utc)
        for record in rows
    )
    return [
        QualityResult(
            "vacancy_id_unique", "critical", len(ids) == len(set(ids)), len(ids), len(set(ids))
        ),
        QualityResult("published_at_not_future", "critical", invalid_dates == 0, invalid_dates, 0),
    ]
