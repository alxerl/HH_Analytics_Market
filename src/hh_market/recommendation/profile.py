"""Validated, synthetic candidate profile contract."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    target_roles: list[str] = Field(min_length=1)
    target_seniority: str | None = None
    current_skills: set[str] = Field(default_factory=set)
    preferred_skills: set[str] = Field(default_factory=set)
    excluded_employers: set[str] = Field(default_factory=set)
    locations: set[int] = Field(default_factory=set)
    salary_floor_rub: int | None = Field(default=None, ge=0)


def load_profile(path: Path) -> CandidateProfile:
    with path.open(encoding="utf-8") as stream:
        payload: Any = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise ValueError("Profile must contain a YAML object")
    return CandidateProfile.model_validate(payload)
