"""Resumable collection of HeadHunter vacancy-search pages."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from ..config import SearchQuery
from .checkpoint import CompletedPage, load_manifest, save_manifest
from .raw_store import RawStore


class VacancySearchClient(Protocol):
    def get(self, path: str, params: dict[str, str | int]) -> dict[str, object]: ...


@dataclass(frozen=True)
class CollectionSummary:
    pages_collected: int
    pages_skipped: int
    items_collected: int


def collect_queries(
    client: VacancySearchClient,
    queries: list[SearchQuery],
    snapshot_date: date,
    raw_root: Path,
    *,
    resume: bool,
    include_details: bool = False,
) -> CollectionSummary:
    store = RawStore(raw_root)
    manifest_path = raw_root / snapshot_date.isoformat() / "manifest.json"
    manifest = load_manifest(manifest_path) if resume else load_manifest(manifest_path)
    collected = skipped = items_collected = 0
    details: dict[str, dict[str, object]] = {}

    for query in queries:
        for area_id in query.areas:
            for page_no in range(query.pages_cap):
                if resume and manifest.includes(query.id, area_id, page_no):
                    skipped += 1
                    completed = manifest.get(query.id, area_id, page_no)
                    if completed is not None and completed.items_count == 0:
                        break
                    continue
                payload = client.get(
                    "/vacancies",
                    params={"text": query.text, "area": area_id, "page": page_no, "per_page": 100},
                )
                items = payload.get("items", [])
                if not isinstance(items, list):
                    raise ValueError("HH API field 'items' must be a list")
                if include_details:
                    enriched = []
                    for item in items:
                        if not isinstance(item, dict) or item.get("id") is None:
                            raise ValueError("Vacancy search item has no id")
                        vacancy_id = str(item["id"])
                        if vacancy_id not in details:
                            details[vacancy_id] = client.get(f"/vacancies/{vacancy_id}", params={})
                        enriched.append(details[vacancy_id])
                    payload["items"] = enriched
                artifact = store.write_json(snapshot_date, query.id, area_id, page_no, payload)
                manifest.add(
                    CompletedPage(
                        query_id=query.id,
                        area_id=area_id,
                        page_no=page_no,
                        raw_path=str(artifact.path.relative_to(raw_root)),
                        sha256=artifact.sha256,
                        items_count=len(items),
                    )
                )
                save_manifest(manifest_path, manifest)
                collected += 1
                items_collected += len(items)
                total_pages = payload.get("pages")
                if not items or isinstance(total_pages, int) and page_no + 1 >= total_pages:
                    break
    return CollectionSummary(collected, skipped, items_collected)
