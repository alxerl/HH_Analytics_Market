CREATE OR REPLACE VIEW mart.market_daily AS
SELECT
  as_of_date,
  role,
  seniority,
  area_id,
  area_name,
  count(*) AS active_vacancies,
  count(DISTINCT vacancy_id) AS unique_vacancies,
  count(*) FILTER (WHERE midpoint_rub IS NOT NULL)::numeric / NULLIF(count(*), 0) AS salary_coverage
FROM mart.vacancy_current
GROUP BY as_of_date, role, seniority, area_id, area_name;

CREATE OR REPLACE VIEW mart.skill_demand_daily AS
SELECT
  current.as_of_date,
  current.role,
  current.seniority,
  skill.canonical_name AS skill,
  count(DISTINCT current.vacancy_id) AS vacancy_count
FROM mart.vacancy_current AS current
JOIN core.vacancy_skills AS vacancy_skill ON vacancy_skill.vacancy_id = current.vacancy_id
JOIN core.skills AS skill ON skill.skill_id = vacancy_skill.skill_id
GROUP BY current.as_of_date, current.role, current.seniority, skill.canonical_name;

CREATE OR REPLACE VIEW mart.salary_distribution AS
SELECT
  as_of_date,
  role,
  seniority,
  area_id,
  area_name,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY midpoint_rub) AS median_salary_midpoint,
  percentile_cont(0.25) WITHIN GROUP (ORDER BY midpoint_rub) AS p25_salary_midpoint,
  percentile_cont(0.75) WITHIN GROUP (ORDER BY midpoint_rub) AS p75_salary_midpoint,
  count(*) FILTER (WHERE midpoint_rub IS NOT NULL) AS salary_observations
FROM mart.vacancy_current
GROUP BY as_of_date, role, seniority, area_id, area_name;

CREATE OR REPLACE VIEW mart.employer_activity AS
SELECT
  current.as_of_date,
  employer.employer_id,
  employer.name AS employer_name,
  current.role,
  count(DISTINCT current.vacancy_id) AS active_vacancies
FROM mart.vacancy_current AS current
JOIN core.vacancies AS vacancy ON vacancy.vacancy_id = current.vacancy_id
LEFT JOIN core.employers AS employer ON employer.employer_id = vacancy.employer_id
GROUP BY current.as_of_date, employer.employer_id, employer.name, current.role;
