from decimal import Decimal

from hh_market.transform.clean_text import html_to_text, normalize_text
from hh_market.transform.salary import normalize_salary


def test_html_cleaning_handles_entities_and_whitespace() -> None:
    assert html_to_text("<p>SQL&nbsp;&amp; Python</p><br> analyst") == "SQL & Python analyst"
    assert normalize_text("<b>Data Analyst</b>") == "data analyst"


def test_salary_keeps_unknown_as_null_and_supports_bounds() -> None:
    assert normalize_salary(None, None, "RUR").status == "missing"
    result = normalize_salary(100, 200, "USD", fx_to_rub=Decimal("90"))
    assert result.from_rub == Decimal("9000")
    assert result.midpoint_rub == Decimal("13500")


def test_salary_rejects_invalid_range() -> None:
    assert normalize_salary(200, 100, "RUR").status == "invalid"
