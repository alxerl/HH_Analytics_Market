"""Validated application configuration and search query loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HH_MARKET_", env_file=".env", extra="ignore")

    api_base_url: str = "https://api.hh.ru"
    database_url: str = "postgresql://hh_market:hh_market@localhost:5432/hh_market"
    raw_root: Path = Path("data/raw")
    log_level: str = "INFO"
    api_timeout_seconds: float = Field(default=30, gt=0)
    api_max_retries: int = Field(default=4, ge=0, le=10)


class SearchQuery(BaseModel):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    text: str = Field(min_length=1)
    areas: list[int] = Field(min_length=1)
    pages_cap: int = Field(default=5, ge=1, le=200)
    active: bool = True


class SearchQuerySet(BaseModel):
    version: str = Field(min_length=1)
    queries: list[SearchQuery] = Field(min_length=1)

    def active_queries(self) -> list[SearchQuery]:
        return [query for query in self.queries if query.active]


def load_search_queries(path: Path) -> SearchQuerySet:
    """Load and validate the versioned search configuration."""
    if not path.is_file():
        raise FileNotFoundError(f"Search query config does not exist: {path}")
    with path.open(encoding="utf-8") as stream:
        payload: Any = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise ValueError("Search query config must contain a YAML object")
    return SearchQuerySet.model_validate(payload)
