"""Salary normalization without inventing missing values."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class SalaryResult:
    from_rub: Decimal | None
    to_rub: Decimal | None
    midpoint_rub: Decimal | None
    status: Literal["normalized", "missing", "unsupported_currency", "invalid"]


def normalize_salary(
    from_value: int | float | None,
    to_value: int | float | None,
    currency: str | None,
    *,
    fx_to_rub: Decimal | None = None,
) -> SalaryResult:
    if from_value is None and to_value is None:
        return SalaryResult(None, None, None, "missing")
    if currency is None or fx_to_rub is None and currency != "RUR":
        return SalaryResult(None, None, None, "unsupported_currency")
    try:
        lower = Decimal(str(from_value)) if from_value is not None else None
        upper = Decimal(str(to_value)) if to_value is not None else None
    except (ArithmeticError, ValueError):
        return SalaryResult(None, None, None, "invalid")
    if lower is not None and lower < 0 or upper is not None and upper < 0:
        return SalaryResult(None, None, None, "invalid")
    if lower is not None and upper is not None and lower > upper:
        return SalaryResult(None, None, None, "invalid")
    rate = Decimal("1") if currency == "RUR" else fx_to_rub
    assert rate is not None
    lower_rub = lower * rate if lower is not None else None
    upper_rub = upper * rate if upper is not None else None
    midpoint = (
        (lower_rub + upper_rub) / 2
        if lower_rub is not None and upper_rub is not None
        else lower_rub or upper_rub
    )
    return SalaryResult(lower_rub, upper_rub, midpoint, "normalized")
