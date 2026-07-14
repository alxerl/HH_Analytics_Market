# Архитектура и контракты

## Слои

- `raw`: append-only отражение API. Никаких исправлений значений.
- `core`: типизированные канонические сущности и история публикаций.
- `ml`: признаки, labels, predictions, версии правил/моделей.
- `mart`: стабильные grains для BI и рекомендаций.
- `ops`: runs, checkpoints, DQ и технические события.

## Инварианты

1. Каждый downstream row связан с `run_id`, `snapshot_date` и исходной вакансией.
2. Raw-файл считается принятым только после checksum и записи manifest.
3. Повторный запуск одинаковых входов даёт одинаковый результат.
4. Исторический snapshot не перезаписывается.
5. Исходные и нормализованные значения хранятся раздельно.
6. Любой prediction содержит `model_version`/`rules_version` и confidence.
7. Витрины явно фиксируют grain и `as_of_date`.

## Инкрементальный сбор

Ключ batch: `(snapshot_date, search_query_id, area_id, page)`. Для каждого запроса сохранять URL без секретов, параметры, HTTP status, requested/received timestamps, page/items/found, checksum и путь raw. При рестарте читать checkpoint и повторять только незавершённые страницы. Ответ сначала писать во временный файл, затем атомарно переименовывать.

API detail-запросы отделить от search-запросов. Поиск формирует список IDs; детальная карточка загружается для новых либо изменившихся/просроченных вакансий. Политику refresh сделать конфигурируемой.

## Ошибки и повторения

- Retry: timeout, connection reset, 429 и 5xx; exponential backoff + jitter.
- Не retry: большинство 4xx; записать ошибку и завершить соответствующим статусом.
- Ограничить число попыток и общее время.
- Не логировать токены, полный HTML и персональные данные.
- Run statuses: `started`, `partial`, `succeeded`, `failed`.

## CLI-контракт

- `collect --date --query-set --area --resume`
- `transform --run-id|--date`
- `train --target role --dataset-version`
- `evaluate --model-version`
- `predict --model-version --date`
- `build-marts --as-of-date`
- `recommend --profile --top`
- `quality --run-id --fail-on`

Каждая команда: `--help`, ненулевой exit code при ошибке, summary в stdout, подробности в structured log.

## Конфигурация

Приоритет: CLI > environment > YAML defaults. Конфиг валидируется при старте. `search_queries.yml` содержит id, text, areas, pages cap, active. Правила и словарь навыков имеют semver и дату вступления.

## Безопасность и приватность

В MVP не хранить резюме и персональные профили пользователей в БД. Example profile синтетический. Секреты не попадают в артефакты CI. Raw retention и лицензирование данных HH явно описать перед публичной публикацией набора данных.

## Наблюдаемость

На run: длительность, запросы/ошибки API, pages/items, new/updated rows, duplicates, null salary share, unknown role share, DQ failures, freshness. Логи коррелируются по `run_id`.
