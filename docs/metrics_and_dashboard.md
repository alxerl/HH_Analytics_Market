# Метрики и ТЗ на дашборд

## Общие правила

- Базовая единица рынка: representative vacancy, чтобы повторные публикации не раздували показатели.
- Все страницы имеют `as_of_date`, период, area, role, seniority, employment, schedule.
- Salary coverage показывается рядом с зарплатной статистикой.
- Median/percentiles предпочтительнее среднего для зарплат.
- Любая карточка должна иметь SQL source и grain.

## Страница 1 - Market overview

| Визуал | Метрика / источник | Управленческий вопрос |
|---|---|---|
| KPI cards | active vacancies, new, employers, salary coverage / `mart.market_daily` | размер и свежесть рынка |
| Line | new representative vacancies by day | растёт ли спрос |
| Stacked bars | share by role/seniority | кого ищут |
| Map/bar | vacancies by area | где спрос |
| Table | top titles/query coverage | что реально вошло в выборку |

## Страница 2 - Skills

Top skills bar, role x skill heatmap, trend of selected skills, co-occurrence matrix/network (только если читаемо), skill coverage. Источник `mart.skill_demand_daily`. Метрика: вакансии с skill / вакансии в сегменте.

## Страница 3 - Salaries

Median, P25/P75, box plot по роли/seniority/area, salary coverage, gross/net/currency policy. Источник `mart.salary_distribution`. Не смешивать неизвестные и нулевые зарплаты.

## Страница 4 - Employers

Top employers by unique vacancies, role mix, salary coverage/median, repeat-publication rate, trend. Не интерпретировать повторную публикацию автоматически как рост штата.

## Страница 5 - Vacancy matching

Профиль/версия scoring, top-N table, total/component scores, matched/missing skills, salary, seniority, published date, URL. Фильтры работают до ranking либо правило явно задокументировано.

## Каталог ключевых метрик

- `active_vacancies`: representative publications active на as-of.
- `new_vacancies`: first_seen_date в периоде.
- `repeat_publication_rate`: publications in duplicate/repost cluster / publications.
- `skill_share`: unique representative vacancies with skill / eligible vacancies.
- `salary_coverage`: vacancies with usable normalized boundary / eligible vacancies.
- `median_salary_midpoint`: median midpoint только там, где обе границы; отдельно lower/upper-only coverage.
- `classification_coverage`: predictions не `unclear` / predicted vacancies.
- `freshness_lag`: now - latest successful snapshot.

## Приёмка BI

Для каждого визуала: название, grain, SQL/view, формула, формат, фильтры, default period, tooltip, empty state. Три контрольных среза вручную сверяются с SQL; cross-filtering не меняет denominator неожиданно; дата обновления видна.
