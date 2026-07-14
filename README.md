# HH Analytics Market

Reproducible pipeline for collecting HeadHunter analyst vacancies, preserving raw snapshots,
normalizing market signals, and preparing explainable matching outputs. The repository is ready
for a public GitHub push: dependencies are locked, CI is configured, generated data is excluded,
and every implemented behaviour is covered by automated checks.

## What works now

- validated YAML configuration and a `hh-market` CLI;
- resumable HeadHunter vacancy collection with retry, pagination stop rules, atomic raw JSON and
  checksum manifest;
- deterministic HTML cleanup, salary normalization, exact/near duplicate checks, skill extraction,
  seniority baseline and explainable vacancy scoring;
- initial PostgreSQL schema for `ops`, `raw`, and `core` plus Docker Compose;
- unit tests, Ruff, mypy, pre-commit, GitHub Actions and Dependabot.

The architecture, data contracts, remaining roadmap and BI specification are deliberately kept in
[`docs/`](docs/) so that data loading, model training and marts can be added without changing the
public contracts.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --frozen
uv run hh-market --help
uv run pytest
uv run ruff check .
uv run mypy
```

Copy `.env.example` to `.env` only when overriding defaults. Never commit `.env`.

## Collect vacancies

```bash
uv run hh-market collect --date 2026-07-14 --query-set config/search_queries.yml
uv run hh-market collect --date 2026-07-14 --resume
uv run hh-market transform --date 2026-07-14
uv run hh-market migrate
uv run hh-market load --date 2026-07-14
uv run hh-market train --dataset data/labeling/gold_labels.csv --model-version v0.1.0
uv run hh-market predict --model-path models/role-v0.1.0.joblib --model-version v0.1.0
uv run hh-market build-marts
uv run hh-market quality --date 2026-07-14 --fail-on critical
uv run hh-market recommend --date 2026-07-14 --profile data/profiles/example_profile.yml --top 20
```

Responses are written below `data/raw/<snapshot-date>/`; this directory is intentionally ignored
by Git. `manifest.json` records accepted pages, paths and checksums. The public HH API terms and
data-retention policy must be reviewed before publishing or redistributing any collected data.

`transform` builds `reports/transformed-<date>.json` with canonical vacancy records, rule-based
role labels, dictionary skills and data-quality results. Reports remain local and are not committed.

For the database-backed path, run `migrate`, `load`, `predict`, `quality`, then `recommend`. The
daily GitHub Actions workflow executes this sequence and stores generated reports as short-lived
artifacts. See [the runbook](docs/runbook.md) and [BI dataset contract](dashboard/README.md).

Before release, follow the [clean-room checklist](docs/clean_room_checklist.md). The
[executive-report policy](docs/executive_report.md) prevents conclusions outside the observed
period or unsupported by a stable mart.

## Local database

```bash
docker compose up -d db
```

The initial schema is in [`migrations/001_initial.sql`](migrations/001_initial.sql). Docker is not
required for unit tests.

## Quality gates

```bash
make check
# or: uv run ruff check . && uv run mypy && uv run pytest
```

CI runs these checks on Python 3.12 and 3.13 for pull requests and pushes to `main`.

## Documentation

- [Architecture](docs/architecture.md)
- [Data model](docs/data_model.md)
- [ML and matching](docs/ml_and_matching.md)
- [Dashboard specification](docs/metrics_and_dashboard.md)
- [Data quality and testing](docs/data_quality_and_tests.md)
- [Implementation roadmap](IMPLEMENTATION_PLAN.md)

## License

Distributed under the [MIT License](LICENSE).
