# Data quality и тестирование

## Severity

- Critical: нарушена целостность/невозможно строить данные; pipeline fail.
- Warning: результат можно построить, но требуется внимание.
- Info: наблюдение/trend.

## Проверки данных

| Проверка | Порог/реакция |
|---|---|
| `vacancy_id` заполнен и уникален в current grain | 0 ошибок, critical |
| snapshot связан с request/run | 0 orphan, critical |
| даты логичны, нет далёкого будущего | 0 critical; допуск clock skew документировать |
| raw payload/path/checksum доступны | 100%, critical |
| key fields name/published/description | baseline + drift warning |
| salary boundaries не отрицательны, from <= to | 0 ошибок, critical |
| валюта/категории известны | unknown share report; резкий скачок warning |
| duplicate representative ровно один на cluster | 0 ошибок, critical |
| prediction имеет версию и допустимый class | 0 ошибок, critical |
| skill FK/словарь согласованы | 0 orphan, critical |
| daily freshness | warning после SLA, critical после согласованного окна |
| объём API и новых вакансий | относительный drift к rolling baseline |

Результат сохранять в `ops.quality_results(check_name, run_id, severity, passed, observed, expected, sample, checked_at)` и JSON/Markdown artifact.

## Пирамида тестов

- Unit: text cleaning, salary cases, aliases, rule precedence, score components, deterministic tie-break.
- Contract: сохранённые обезличенные API fixtures против parser/schema.
- Integration: PostgreSQL migrations, loaders, idempotency, mart reconciliation.
- ML: no leakage groups, feature schema, deterministic seed, metric regression tolerance.
- End-to-end smoke: одна query/page fixture -> raw -> core -> predictions -> marts -> recommendation.

## Обязательные edge cases

Пустая страница API; 429 затем success; оборванный JSON; вакансия без employer/description/salary; валюта не RUB; только salary from/to; gross unknown; HTML entities; русский/английский title; `R` как отдельный skill; одинаковый текст разных работодателей; изменённая вакансия с тем же ID; missing профильный параметр.

## CI gates

PR: lint, types, unit, contract, migration smoke. Main/nightly: integration, ML regression, end-to-end. Coverage использовать как сигнал; критические трансформеры и scoring должны иметь branch tests, а не только высокий общий процент.
