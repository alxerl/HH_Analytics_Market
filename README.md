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

## Визуальный результат и запуск без HH API

После успешного `collect` и `transform`:

```bash
uv run hh-market report --date 2026-09-04
```

Результат: `reports/dashboard-2026-09-04/overview.png`, `summary.json` и README.
Это локальный отчёт о наблюдаемой выборке, не интерактивный сайт.
В нём уникальные ID; агрегация representative vacancies после поиска близких дублей
остаётся в SQL-витринах.

Для проверки без доступа к API используйте **отдельный учебный каталог**:

```powershell
$env:HH_MARKET_RAW_ROOT = 'data/demo-raw'
uv run hh-market demo --date 2026-09-04
uv run hh-market transform --date 2026-09-04 --reports-root reports/demo
uv run hh-market report --date 2026-09-04 --reports-root reports/demo
```

Demo содержит 12 синтетических вакансий из `gold_labels.csv`; график помечен SYNTHETIC.
Повторный `demo` не перезаписывает существующий срез. Для повторного просмотра достаточно
`transform` и `report`. Перед живым сбором уберите переменную учебного каталога.
Учебную базу следует держать отдельно от базы живых данных.

Если HH вернул 401/403, CLI выводит тип ошибки и request_id и прекращает сбор.
При необходимой авторизации задайте `HH_MARKET_API_ACCESS_TOKEN` в локальном `.env`
и разрешённый `HH_MARKET_API_USER_AGENT`. Токен не хранится в репозитории.
Отказ доступа не заменяется фиктивными рыночными данными. `collect` загружает полные
описания вакансий, необходимые для извлечения навыков.

Для PostgreSQL Docker необязателен: можно указать URL уже запущенного PostgreSQL 16+
в `HH_MARKET_DATABASE_URL`. Интеграционным тестам нужен отдельный
`HH_MARKET_INTEGRATION_DB_URL`.

Обучение на поставляемых 12 строках — только smoke check: оно не доказывает качество
модели на реальном рынке; нужна независимая размеченная выборка.

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
