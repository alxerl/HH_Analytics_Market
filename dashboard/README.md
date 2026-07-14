# BI dataset contract

BI connects only to the `mart` schema. Refresh after a successful `quality` run; display the
latest `as_of_date` in every page header. All counts use representative active vacancies.

| Page | Dataset | Grain | Core visuals |
|---|---|---|---|
| Market overview | `mart.market_daily` | date x role x seniority x area | active vacancies, salary coverage, role mix, demand by area |
| Skills | `mart.skill_demand_daily` | date x role x seniority x skill | top skills, heatmap, skill share trends |
| Salaries | `mart.salary_distribution` | date x role x seniority x area | median/P25/P75 and coverage |
| Employers | `mart.employer_activity` | date x employer x role | unique vacancies and role mix |
| Matching | `reports/recommendations-<date>.json` | vacancy | total score, factors, matched/missing skills |

Shared filters: `as_of_date`, `area_id`, `role`, `seniority`. Empty states must distinguish
“no observations” from “salary unavailable”. Do not divide filtered numerators by unfiltered
denominators.
