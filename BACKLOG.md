# Backlog

Формат: ID, результат, зависимости, acceptance. Одна задача должна помещаться в один небольшой PR.

## P0 - каркас и данные

- **HH-001** Каркас репозитория. Acceptance: структура, `uv sync`, lint/test команды и README работают.
- **HH-002** Settings/logging/CLI. Depends HH-001. Acceptance: validated config, masked secrets, `run_id` во всех логах.
- **HH-003** Compose PostgreSQL. Depends HH-001. Acceptance: healthcheck и persistent volume.
- **HH-004** Миграции ops/raw. Depends HH-003. Acceptance: up/down test.
- **HH-005** Миграции core/ml/mart. Depends HH-004. Acceptance: constraints/indexes соответствуют data model.
- **HH-006** Search config schema. Depends HH-002. Acceptance: invalid query set fails fast.
- **HH-007** HH API client. Depends HH-002. Acceptance: timeout, retry, 429, user-agent unit-tested.
- **HH-008** Paginator/rate limit. Depends HH-007. Acceptance: stop rules и page counts tested.
- **HH-009** Atomic raw store/manifest. Depends HH-004,008. Acceptance: checksum, no partial accepted files.
- **HH-010** Checkpoint/resume. Depends HH-009. Acceptance: interrupted fixture resumes without duplicate.

## P0 - трансформации

- **HH-011** Snapshot loader. Depends HH-009. Acceptance: idempotent insert and provenance.
- **HH-012** HTML/text cleaner. Depends HH-011. Acceptance: fixture golden tests.
- **HH-013** Core vacancy/employer upsert. Depends HH-005,012. Acceptance: first/last seen correct.
- **HH-014** Salary normalizer. Depends HH-013. Acceptance: missing/bounds/gross/currency cases.
- **HH-015** Publication history. Depends HH-013. Acceptance: changed payload produces history, not overwrite.
- **HH-016** Exact duplicates. Depends HH-015. Acceptance: deterministic representative.
- **HH-017** Near-duplicate candidates/scoring. Depends HH-016. Acceptance: labeled pair evaluation report.

## P1 - классификация и навыки

- **HH-018** Labeling guide/sample. Depends HH-013. Acceptance: versioned guide and stratified sample.
- **HH-019** Rule role baseline. Depends HH-018. Acceptance: per-class report.
- **HH-020** TF-IDF LR training. Depends HH-018. Acceptance: grouped/time split, saved pipeline.
- **HH-021** Hybrid inference. Depends HH-019,020. Acceptance: version/confidence/decision path persisted.
- **HH-022** Seniority rules/junior score. Depends HH-018. Acceptance: component explanations and edge tests.
- **HH-023** Skill dictionary/extractor. Depends HH-013. Acceptance: alias/boundary tests and versioned results.
- **HH-024** Model card/error analysis. Depends HH-020,021,023. Acceptance: reproducible metrics and limitations.

## P1 - продуктовый слой

- **HH-025** Current/market marts. Depends HH-015,017,021,022. Acceptance: grain uniqueness and totals reconciliation.
- **HH-026** Skills/salary/employer marts. Depends HH-014,023,025. Acceptance: catalog SQL checks.
- **HH-027** Profile schema. Depends HH-002. Acceptance: example and invalid config tests.
- **HH-028** Matching score/explanations. Depends HH-021,022,023,027. Acceptance: deterministic ranked fixture.
- **HH-029** DQ runner/report. Depends HH-025,026. Acceptance: severity-based exit and persisted report.
- **HH-030** Dashboard dataset/TZ. Depends HH-025,026,028. Acceptance: every visual mapped to view/metric.
- **HH-031** Dashboard/screenshots. Depends HH-030. Acceptance: 5 pages and SQL reconciliation.

## P2 - завершение

- **HH-032** Daily CI workflow. Depends HH-010,029. Acceptance: manual + schedule, concurrency lock, artifacts.
- **HH-033** Clean-room runbook. Depends all P0/P1. Acceptance: fresh machine walkthrough.
- **HH-034** Executive report. Depends HH-031,033. Acceptance: conclusions tied to observed period and limitations.
- **HH-035** Portfolio polish/release v1.0. Depends HH-034. Acceptance: badges, screenshots, model card, no placeholders/secrets.
