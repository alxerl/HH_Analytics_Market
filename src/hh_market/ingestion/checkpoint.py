"""Persistent, atomic collection manifests used for resume."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CompletedPage:
    query_id: str
    area_id: int
    page_no: int
    raw_path: str
    sha256: str
    items_count: int


@dataclass
class CollectionManifest:
    completed_pages: list[CompletedPage] = field(default_factory=list)

    def includes(self, query_id: str, area_id: int, page_no: int) -> bool:
        return self.get(query_id, area_id, page_no) is not None

    def get(self, query_id: str, area_id: int, page_no: int) -> CompletedPage | None:
        return next(
            (
                item
                for item in self.completed_pages
                if item.query_id == query_id and item.area_id == area_id and item.page_no == page_no
            ),
            None,
        )

    def add(self, page: CompletedPage) -> None:
        if not self.includes(page.query_id, page.area_id, page.page_no):
            self.completed_pages.append(page)


def load_manifest(path: Path) -> CollectionManifest:
    if not path.is_file():
        return CollectionManifest()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CollectionManifest(
        completed_pages=[CompletedPage(**item) for item in payload.get("completed_pages", [])]
    )


def save_manifest(path: Path, manifest: CollectionManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = {"completed_pages": [asdict(item) for item in manifest.completed_pages]}
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(path)
