"""Local visual report from a successfully transformed, labelled snapshot."""

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .ingestion.raw_store import RawStore


def create_demo(snapshot_date: date, raw_root: Path, labels: Path) -> None:
    """Explicit synthetic fixture; never a fallback for denied live API access."""
    if any((raw_root / snapshot_date.isoformat()).rglob("page-*.json")):
        raise ValueError("Snapshot already contains data; use a separate raw root for demo")
    with labels.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    items = [
        {
            "id": f"demo-{row['vacancy_id']}",
            "name": row["title"],
            "description": row["description"],
            "area": {"id": "1", "name": "Demo"},
            "employer": {"id": "demo", "name": "Synthetic employer"},
            "published_at": snapshot_date.isoformat() + "T00:00:00+00:00",
        }
        for row in rows
    ]
    RawStore(raw_root).write_json(
        snapshot_date, "demo", 1, 0, {"items": items, "found": len(items), "source": "synthetic"}
    )


def write_report(reports_root: Path, snapshot_date: date) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    source = reports_root / f"transformed-{snapshot_date.isoformat()}.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    records = payload["records"]
    if not records:
        raise ValueError("Snapshot is empty: no market report can be produced")
    synthetic = all(str(row["vacancy_id"]).startswith("demo-") for row in records)
    roles = Counter(row["role"]["label"] for row in records)
    skills = Counter(skill["canonical_name"] for row in records for skill in row["skills"])
    folder = reports_root / f"dashboard-{snapshot_date.isoformat()}"
    folder.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for ax, counts, title in zip(
        axes, [roles, skills], ["Roles", "Skills in descriptions"], strict=True
    ):
        values = counts.most_common(10)
        ax.barh([x[0] for x in values][::-1], [x[1] for x in values][::-1], color="#237b99")
        ax.set_title(title)
        ax.set_xlabel("Unique vacancy IDs")
        if not values:
            ax.text(0.5, 0.5, "No observations", transform=ax.transAxes, ha="center")
    label = "SYNTHETIC DEMO — not the real job market" if synthetic else "Observed HH sample"
    fig.suptitle(f"{label} | {snapshot_date} | n={len(records)}")
    fig.savefig(folder / "overview.png", dpi=140)
    plt.close(fig)
    summary = {
        "snapshot_date": str(snapshot_date),
        "synthetic": synthetic,
        "unique_vacancies": len(records),
        "roles": dict(roles),
        "skills": dict(skills),
    }
    (folder / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (folder / "README.md").write_text(
        f"# {label}\n\nSnapshot: {snapshot_date}; unique IDs: {len(records)}.\n\n"
        "![Overview](overview.png)\n\n"
        "Counts describe this collected sample only. Similar vacancies with different IDs "
        "may remain; database deduplication is a separate stage. "
        "Salary distributions require the database marts; missing pay is not zero.\n",
        encoding="utf-8",
    )
    return {**summary, "output": str(folder)}
