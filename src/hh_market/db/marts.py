"""Validation summary for SQL mart views."""

import psycopg


def build_marts(database_url: str) -> dict[str, int]:
    """Views are declarative; querying them verifies they are executable and reports their size."""
    names = (
        "vacancy_current",
        "market_daily",
        "skill_demand_daily",
        "salary_distribution",
        "employer_activity",
    )
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            result: dict[str, int] = {}
            for name in names:
                row = cursor.execute(f"SELECT count(*) FROM mart.{name}").fetchone()
                assert row is not None
                result[name] = int(row[0])
            return result
