"""Command-line entrypoint for the HH Analytics Market pipeline."""

import argparse
import logging
import sys
import uuid
from datetime import date
from pathlib import Path

from . import __version__
from .api.client import HHClient
from .config import Settings, load_search_queries
from .ingestion.collector import collect_queries
from .logging import configure_logging
from .pipeline import transform_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hh-market", description="HH Analytics Market pipeline")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect vacancy snapshots")
    collect.add_argument(
        "--date", dest="snapshot_date", type=date.fromisoformat, default=date.today()
    )
    collect.add_argument("--query-set", type=Path, default=Path("config/search_queries.yml"))
    collect.add_argument("--area", type=int, action="append")
    collect.add_argument("--resume", action="store_true")

    transform = subparsers.add_parser("transform", help="Transform raw snapshots")
    transform.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    transform.add_argument("--skills", type=Path, default=Path("config/skills.yml"))
    transform.add_argument("--reports-root", type=Path, default=Path("reports"))

    for name, help_text in (
        ("train", "Train a model"),
        ("evaluate", "Evaluate a model"),
        ("predict", "Predict vacancy labels"),
        ("build-marts", "Build analytical marts"),
        ("recommend", "Recommend vacancies"),
        ("quality", "Run data quality checks"),
    ):
        subparsers.add_parser(name, help=help_text)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(Settings().log_level)
    run_id = str(uuid.uuid4())
    logger = logging.getLogger("hh_market.cli")
    logger.info("command_started", extra={"run_id": run_id})
    if args.command == "collect":
        query_set = load_search_queries(args.query_set)
        selected = [
            q
            for q in query_set.active_queries()
            if not args.area or any(area in q.areas for area in args.area)
        ]
        if not selected:
            raise SystemExit("No active search queries match the selected area")
        settings = Settings()
        with HHClient(
            base_url=settings.api_base_url,
            timeout=settings.api_timeout_seconds,
            max_retries=settings.api_max_retries,
        ) as client:
            summary = collect_queries(
                client, selected, args.snapshot_date, settings.raw_root, resume=args.resume
            )
        print(
            f"run_id={run_id} snapshot_date={args.snapshot_date.isoformat()} "
            f"pages_collected={summary.pages_collected} pages_skipped={summary.pages_skipped} "
            f"items_collected={summary.items_collected}"
        )
        return 0
    if args.command == "transform":
        settings = Settings()
        transform_summary = transform_snapshot(
            settings.raw_root, args.snapshot_date, args.skills, args.reports_root
        )
        print(
            f"run_id={run_id} snapshot_date={args.snapshot_date.isoformat()} "
            f"records={transform_summary['records']} "
            f"quality_failures={transform_summary['quality_failures']}"
        )
        return 0
    print(f"run_id={run_id} command={args.command} (implementation scheduled by phase plan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
