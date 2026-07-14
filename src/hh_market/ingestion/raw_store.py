"""Append-only atomic storage for raw API responses."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawArtifact:
    path: Path
    sha256: str
    bytes_written: int


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write_json(
        self,
        snapshot_date: date,
        query_id: str,
        area_id: int,
        page_no: int,
        payload: dict[str, Any],
    ) -> RawArtifact:
        target = (
            self.root
            / snapshot_date.isoformat()
            / query_id
            / str(area_id)
            / f"page-{page_no:04d}.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        fd, temporary = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return RawArtifact(target, digest, len(encoded))
