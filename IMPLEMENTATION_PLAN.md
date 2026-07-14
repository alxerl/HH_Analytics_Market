# План реализации HH Analytics Market

## Принцип выполнения

Работать строго по фазам. Следующая фаза начинается только после прохождения gate предыдущей. Каждый PR должен быть малым, содержать тесты, команды проверки и обновление документации.

| Фаза | Результат | Зависит от | Gate |
|---|---|---|---|
| 0. Bootstrap | каркас, CI, конфиг, логирование | - | lint/test запускаются локально и в CI |
| 1. Data contracts | DDL, миграции, справочники, ER | 0 | миграции up/down, schema tests |
| 2. Collection | API client, pagination, retry, raw snapshots | 1 | повторный сбор идемпотентен |
| 3. Core transform | очистка, HTML/text, salary, dates | 2 | fixture превращается в ожидаемую запись |
| 4. Dedup | exact и near-duplicate publications | 3 | precision ручной выборки приемлема |
| 5. Labels/baseline | инструкция разметки, rules | 3 | gold set согласован, baseline посчитан |
| 6. ML/hybrid | TF-IDF+LR, evaluation, registry | 5 | нет leakage, отчёт воспроизводим |
| 7. Skills/seniority | навыки, junior score | 3,5 | тесты терминов и граничных кейсов |
| 8. Marts | market/skills/salary/employer | 4,6,7 | сверка totals с core |
| 9. Matching | профиль, score, explanations | 6,7 | deterministic top-N и объяснения |
| 10. BI/report | 5 страниц, summary | 8,9 | все числа трассируются к SQL |
| 11. Hardening | CI, daily job, observability | все | полный clean-room run |

## Фаза 0 - Bootstrap

- Создать структуру из README, `pyproject.toml`, lock, `.env.example`, Compose.
- Настроить `ruff`, `mypy`, `pytest`, coverage и pre-commit.
- Ввести `run_id`, structured logging, единый класс настроек и CLI shell.
- Добавить CI: install -> lint -> typecheck -> unit tests.

Приёмка: пустая БД поднимается; `--help` работает; секреты отсутствуют; CI зелёный.

## Фаза 1 - Данные

- Реализовать схемы `raw`, `core`, `ml`, `mart`, `ops`.
- Создать таблицы из `docs/data_model.md`, enum/check constraints и индексы.
- Ввести `ops.pipeline_runs`, `ops.quality_results`, версии правил/моделей.
- Добавить seed справочников ролей, навыков, валют и регионов.

Приёмка: миграции применяются к чистой БД и откатываются; ключи и уникальности протестированы.

## Фаза 2 - Сбор

- Клиент API с timeout, retry/backoff, обработкой 429/5xx, user-agent и rate limit.
- Пагинация, набор поисковых запросов, регионы, manifest запроса.
- Сначала атомарно сохранить raw response, затем отметить checkpoint.
- Поддержать resume и повторный запуск без повторной вставки.

Приёмка: тестовый mocked сбор переживает 429, обрыв на странице и resume; количество страниц/элементов сходится.

## Фазы 3-4 - Нормализация и дубли

- Сохранить оригинальный HTML и получить чистый текст отдельно.
- Канонизировать даты, работодателя, location, employment/schedule, experience.
- Зарплату хранить исходно и нормализованно; неизвестное остаётся `NULL`.
- Exact duplicate: `vacancy_id` в рамках snapshot. Near duplicate: нормализованный работодатель + заголовок + cosine similarity текста + временное окно.

Приёмка: трансформация чистая и детерминированная; кластер дублей имеет метод, score и representative vacancy.

## Фазы 5-7 - Аналитические признаки

- Составить labeling guide и стратифицированную gold-выборку.
- Rule baseline до ML; затем TF-IDF word/char n-grams + Logistic Regression.
- Split по времени или группе публикаций, чтобы повторная вакансия не попала в train и test.
- Hybrid: уверенные правила -> ML -> `unclear` ниже порога.
- Skills: canonical dictionary, aliases, boundary-aware matching, negation/sections при необходимости.
- Seniority: явный опыт, title markers, обязанности, hard requirements; сохранить компоненты `junior_score`.

Приёмка: model card содержит dataset/version/split/metrics/confusion matrix/errors; предсказание трассируется.

## Фазы 8-10 - Продуктовый слой

- Материализовать витрины с `as_of_date` и единым правилом выбора representative publication.
- Matching рассчитывать по required/preferred навыкам, роли, seniority, зарплате, региону и свежести.
- Отдавать matched/missing skills и факторы score, а не только число.
- Собрать BI строго по спецификации и executive summary с периодом и ограничениями.

Приёмка: totals между dashboard и SQL совпадают; top-N воспроизводим; нет утверждений вне периода наблюдения.

## Фаза 11 - Эксплуатация

- Daily workflow с ручным запуском, concurrency lock и artifact retention.
- Метрики: run status, API pages, new/changed vacancies, null rates, unknown class share, model drift proxy, freshness.
- Runbook для 429, schema drift, DB unavailable, partial raw file, failed migration.
- Clean-room репетиция по README.

## Рекомендуемая очередность релизов

- v0.1: сбор + raw/core + DQ.
- v0.2: baseline role/seniority/skills + первые витрины.
- v0.3: ML/hybrid + dedup + model card.
- v0.4: matching + dashboard.
- v1.0: CI/daily run, отчёт, скриншоты, воспроизводимость.
