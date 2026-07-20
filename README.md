# HH Analytics Market

[![CI](https://github.com/alxerl/HH_Analytics_Market/actions/workflows/ci.yml/badge.svg)](https://github.com/alxerl/HH_Analytics_Market/actions/workflows/ci.yml) [![Python](https://img.shields.io/badge/python-3.12%2B-3776AB)](https://www.python.org/) [![Лицензия](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Воспроизводимый pipeline для сбора и анализа вакансий аналитиков с HeadHunter.

## Что внутри

- сбор API с retry, пагинацией, resume и checksum raw-файлов;
- детерминированная очистка текста, нормализация зарплат и вакансий;
- поиск точных и близких дублей, признаки ролей, навыков и seniority;
- PostgreSQL-миграции, витрины, предсказания моделей и matching по профилю;
- CLI, Docker Compose, CI, тесты, Ruff и mypy.

## Быстрый запуск

Нужны Python 3.12+, [uv](https://docs.astral.sh/uv/) и Docker для работы с базой.

```bash
uv sync --all-extras --frozen
uv run hh-market --help
uv run pytest
uv run ruff check .
uv run mypy
```

## Запуск pipeline

```bash
docker compose up -d db
uv run hh-market collect --date 2026-07-14 --query-set config/search_queries.yml
uv run hh-market transform --date 2026-07-14
uv run hh-market migrate
uv run hh-market load --date 2026-07-14
uv run hh-market train --dataset data/labeling/gold_labels.csv --model-version v0.1.0
uv run hh-market predict --model-path models/role-v0.1.0.joblib --model-version v0.1.0
uv run hh-market build-marts
uv run hh-market quality --date 2026-07-14 --fail-on critical
uv run hh-market recommend --date 2026-07-14 --profile data/profiles/example_profile.yml --top 20
```

Raw-ответы API, модели и отчёты остаются локальными и игнорируются Git. Перед публикацией данных
проверьте условия использования API и правила хранения.

## Документация

- [Runbook](docs/runbook.md)
- [Архитектура](docs/architecture.md)
- [Модель данных](docs/data_model.md)
- [ML и matching](docs/ml_and_matching.md)
- [Контракт dashboard](dashboard/README.md)
- [Data quality](docs/data_quality_and_tests.md)
- [Правила executive report](docs/executive_report.md)

## Проверки

В репозитории 23 автоматических теста, включая PostgreSQL integration test. CI запускает Python
3.12/3.13, Ruff, mypy и полный набор тестов.

## Лицензия

[MIT](LICENSE)
