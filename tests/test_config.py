from pathlib import Path

import pytest

from hh_market.config import SearchQuerySet, load_search_queries


def test_loads_and_filters_active_queries() -> None:
    config = load_search_queries(Path("config/search_queries.yml"))
    assert len(config.active_queries()) == 2
    assert config.version == "1.0.0"


def test_invalid_query_set_fails_fast() -> None:
    with pytest.raises(ValueError):
        SearchQuerySet.model_validate({"version": "1", "queries": [{"id": "Bad ID"}]})
