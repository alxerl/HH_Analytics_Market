"""Command-line entrypoint for the HH Analytics Market pipeline."""

import argparse
import json
import logging
import sys
import uuid
from datetime import date
from pathlib import Path

from . import __version__
from .api.client import HHClient
from .config import Settings, load_search_queries
from .db.analytics import persist_rule_features
from .db.loaders import load_core_snapshot, load_raw_snapshot
from .db.migrations import apply_migrations
from .ingestion.collector import collect_queries
from .logging import configure_logging
from .pipeline import recommend_from_report, transform_snapshot
from .quality.runner import run_database_quality, should_fail
from .recommendation.profile import load_profile


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

    migrate = subparsers.add_parser("migrate", help="Apply SQL migrations")
    migrate.add_argument("--migrations-dir", type=Path, default=Path("migrations"))

    load = subparsers.add_parser("load", help="Load raw snapshots and canonical core records")
    load.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)

    predict = subparsers.add_parser("predict", help="Persist rule-based role, seniority and skills")
    predict.add_argument("--skills", type=Path, default=Path("config/skills.yml"))

    for name, help_text in (
        ("train", "Train a model"),
        ("evaluate", "Evaluate a model"),
        ("build-marts", "Build analytical marts"),
    ):
        subparsers.add_parser(name, help=help_text)
    quality = subparsers.add_parser("quality", help="Run and persist data-quality checks")
    quality.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    quality.add_argument("--fail-on", choices=("info", "warning", "critical"), default="critical")
    quality.add_argument("--reports-root", type=Path, default=Path("reports"))
    recommend = subparsers.add_parser("recommend", help="Recommend transformed vacancies")
    recommend.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    recommend.add_argument("--profile", type=Path, required=True)
    recommend.add_argument("--top", type=int, default=20)
    recommend.add_argument("--reports-root", type=Path, default=Path("reports"))
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
    if args.command == "migrate":
        migrations = apply_migrations(Settings().database_url, args.migrations_dir)
        print(f"run_id={run_id} migrations_applied={migrations}")
        return 0
    if args.command == "load":
        settings = Settings()
        database_run_id = uuid.UUID(run_id)
        raw_summary = load_raw_snapshot(
            settings.database_url, settings.raw_root, args.snapshot_date, database_run_id
        )
        core_summary = load_core_snapshot(
            settings.database_url, args.snapshot_date, database_run_id
        )
        print(
            f"run_id={run_id} pages={raw_summary['pages']} "
            f"snapshots={raw_summary['vacancy_snapshots']} vacancies={core_summary['vacancies']}"
        )
        return 0
    if args.command == "predict":
        prediction_summary = persist_rule_features(Settings().database_url, args.skills)
        print(
            f"run_id={run_id} predictions={prediction_summary['predictions']} "
            f"skills={prediction_summary['skill_matches']}"
        )
        return 0
    if args.command == "quality":
        results = run_database_quality(
            Settings().database_url, uuid.UUID(run_id), args.snapshot_date, args.reports_root
        )
        failures = sum(not item.passed for item in results)
        print(f"run_id={run_id} checks={len(results)} failures={failures}")
        return 2 if should_fail(results, args.fail_on) else 0
    if args.command == "recommend":
        recommendations = recommend_from_report(
            args.reports_root, args.snapshot_date, load_profile(args.profile), args.top
        )
        print(json.dumps(recommendations, ensure_ascii=False, indent=2))
        return 0
    print(f"run_id={run_id} command={args.command} (implementation scheduled by phase plan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
