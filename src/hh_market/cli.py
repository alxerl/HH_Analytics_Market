"""Command-line entrypoint for the HH Analytics Market pipeline."""

import argparse
import json
import logging
import sys
import uuid
from datetime import date
from pathlib import Path

from . import __version__
from .api.client import HHApiError, HHClient
from .config import Settings, load_search_queries
from .db.analytics import persist_rule_features
from .db.dedup import cluster_publications
from .db.loaders import load_core_snapshot, load_raw_snapshot
from .db.marts import build_marts
from .db.matching import recommend_from_database
from .db.migrations import apply_migrations
from .db.model_predictions import persist_hybrid_predictions
from .ingestion.collector import collect_queries
from .logging import configure_logging
from .models.evaluate import evaluate_role_model
from .models.train import train_role_model
from .pipeline import recommend_from_report, transform_snapshot
from .quality.runner import run_database_quality, should_fail
from .recommendation.profile import load_profile
from .reporting import create_demo, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hh-market", description="HH Analytics Market pipeline")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="Create explicitly synthetic local demo data")
    demo.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    demo.add_argument("--labels", type=Path, default=Path("data/labeling/gold_labels.csv"))
    report = subparsers.add_parser("report", help="Render a local visual snapshot report")
    report.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    report.add_argument("--reports-root", type=Path, default=Path("reports"))

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
    predict.add_argument("--model-path", type=Path)
    predict.add_argument("--model-version")

    train = subparsers.add_parser("train", help="Train a role classifier and model card")
    train.add_argument("--dataset", type=Path, default=Path("data/labeling/gold_labels.csv"))
    train.add_argument("--models-root", type=Path, default=Path("models"))
    train.add_argument("--model-version", default="v0.1.0")

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a trained role classifier")
    evaluate.add_argument("--model-path", type=Path, required=True)
    evaluate.add_argument("--dataset", type=Path, default=Path("data/labeling/gold_labels.csv"))

    subparsers.add_parser("build-marts", help="Validate and summarize mart views")
    quality = subparsers.add_parser("quality", help="Run and persist data-quality checks")
    quality.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    quality.add_argument("--fail-on", choices=("info", "warning", "critical"), default="critical")
    quality.add_argument("--reports-root", type=Path, default=Path("reports"))
    recommend = subparsers.add_parser("recommend", help="Recommend representative market vacancies")
    recommend.add_argument("--date", dest="snapshot_date", type=date.fromisoformat, required=True)
    recommend.add_argument("--profile", type=Path, required=True)
    recommend.add_argument("--top", type=int, default=20)
    recommend.add_argument("--reports-root", type=Path, default=Path("reports"))
    recommend.add_argument(
        "--from-report", action="store_true", help="Use local transformed JSON fallback"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(Settings().log_level)
    run_id = str(uuid.uuid4())
    logger = logging.getLogger("hh_market.cli")
    logger.info("command_started", extra={"run_id": run_id})
    if args.command == "demo":
        create_demo(args.snapshot_date, Settings().raw_root, args.labels)
        print("Synthetic demo created; this is not collected HeadHunter data.")
        return 0
    if args.command == "report":
        print(json.dumps(write_report(args.reports_root, args.snapshot_date), ensure_ascii=False))
        return 0
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
            user_agent=settings.api_user_agent,
            access_token=(settings.api_access_token.get_secret_value()
                          if settings.api_access_token else None),
        ) as client:
            try:
                summary = collect_queries(
                    client, selected, args.snapshot_date, settings.raw_root,
                    resume=args.resume, include_details=True,
                )
            except HHApiError as exc:
                logger.error(str(exc))
                return 2
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
        duplicate_clusters = cluster_publications(settings.database_url, args.snapshot_date)
        print(
            f"run_id={run_id} pages={raw_summary['pages']} "
            f"snapshots={raw_summary['vacancy_snapshots']} vacancies={core_summary['vacancies']} "
            f"duplicate_clusters={duplicate_clusters}"
        )
        return 0
    if args.command == "predict":
        prediction_summary = persist_rule_features(Settings().database_url, args.skills)
        print(
            f"run_id={run_id} predictions={prediction_summary['predictions']} "
            f"skills={prediction_summary['skill_matches']}"
        )
        if args.model_path:
            if not args.model_version:
                raise SystemExit("--model-version is required with --model-path")
            hybrid_summary = persist_hybrid_predictions(
                Settings().database_url, args.model_path, args.model_version
            )
            print(f"hybrid_predictions={hybrid_summary['hybrid_predictions']}")
        return 0
    if args.command == "evaluate":
        macro_f1 = evaluate_role_model(args.model_path, args.dataset)
        print(f"run_id={run_id} macro_f1={macro_f1:.4f}")
        return 0
    if args.command == "build-marts":
        mart_summary = build_marts(Settings().database_url)
        print(json.dumps(mart_summary, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "train":
        training = train_role_model(args.dataset, args.models_root, args.model_version)
        print(
            f"run_id={run_id} model_version={training.model_version} "
            f"macro_f1={training.macro_f1:.4f} model_path={training.model_path}"
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
        profile = load_profile(args.profile)
        recommendations = (
            recommend_from_report(args.reports_root, args.snapshot_date, profile, args.top)
            if args.from_report
            else recommend_from_database(
                Settings().database_url, args.snapshot_date, profile, args.top, args.reports_root
            )
        )
        print(json.dumps(recommendations, ensure_ascii=False, indent=2))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
