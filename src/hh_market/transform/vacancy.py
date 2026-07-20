"""Pure conversion of a HeadHunter payload into a canonical vacancy record."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .clean_text import html_to_text, normalize_text


@dataclass(frozen=True)
class CanonicalVacancy:
    vacancy_id: str
    employer_id: str | None
    employer_name: str | None
    name_raw: str
    name_normalized: str
    description_html: str | None
    description_text: str | None
    area_id: int | None
    area_name: str | None
    published_at: datetime | None
    alternate_url: str | None
    content_hash: str


def canonicalize_vacancy(payload: dict[str, Any]) -> CanonicalVacancy:
    vacancy_id = str(payload["id"])
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Vacancy payload must contain a non-empty name")
    employer_value = payload.get("employer")
    area_value = payload.get("area")
    employer: dict[str, Any] = employer_value if isinstance(employer_value, dict) else {}
    area: dict[str, Any] = area_value if isinstance(area_value, dict) else {}
    description_html = payload.get("description")
    if description_html is not None and not isinstance(description_html, str):
        raise ValueError("Vacancy description must be a string or null")
    published_at = _parse_datetime(payload.get("published_at"))
    stable = {
        "name": name,
        "description": description_html,
        "employer_id": employer.get("id"),
        "area_id": area.get("id"),
    }
    content_hash = hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    area_id = area.get("id")
    return CanonicalVacancy(
        vacancy_id=vacancy_id,
        employer_id=str(employer["id"]) if employer.get("id") is not None else None,
        employer_name=str(employer["name"]) if employer.get("name") is not None else None,
        name_raw=name,
        name_normalized=normalize_text(name) or name.casefold(),
        description_html=description_html,
        description_text=html_to_text(description_html),
        area_id=int(area_id) if area_id is not None else None,
        area_name=str(area["name"]) if area.get("name") is not None else None,
        published_at=published_at,
        alternate_url=str(payload["alternate_url"]) if payload.get("alternate_url") else None,
        content_hash=content_hash,
    )


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("published_at must be an ISO timestamp or null")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
