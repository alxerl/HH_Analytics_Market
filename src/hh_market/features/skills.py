"""Versioned, boundary-aware skill extraction."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillMatch:
    canonical_name: str
    source: str
    match_text: str
    confidence: float


def extract_skills(
    text: str | None, dictionary: dict[str, list[str]], version: str
) -> list[SkillMatch]:
    if not text:
        return []
    found: list[SkillMatch] = []
    for canonical, aliases in dictionary.items():
        candidates = [canonical, *aliases]
        match = next(
            (
                re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, flags=re.IGNORECASE)
                for alias in candidates
            ),
            None,
        )
        if match:
            found.append(SkillMatch(canonical, f"dictionary:{version}", match.group(0), 1.0))
    return sorted(found, key=lambda item: item.canonical_name)
