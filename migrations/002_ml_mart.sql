CREATE TABLE IF NOT EXISTS ops.quality_results (
  quality_result_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id uuid REFERENCES ops.pipeline_runs(run_id),
  check_name text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
  passed boolean NOT NULL,
  observed numeric,
  expected numeric,
  sample jsonb,
  checked_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.skills (
  skill_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  canonical_name text NOT NULL UNIQUE,
  category text,
  active boolean NOT NULL DEFAULT true,
  dictionary_version text NOT NULL
);

CREATE TABLE IF NOT EXISTS core.vacancy_skills (
  vacancy_id text NOT NULL REFERENCES core.vacancies(vacancy_id),
  skill_id bigint NOT NULL REFERENCES core.skills(skill_id),
  source text NOT NULL,
  match_text text NOT NULL,
  section text,
  confidence numeric NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  extractor_version text NOT NULL,
  PRIMARY KEY (vacancy_id, skill_id, extractor_version)
);

CREATE TABLE IF NOT EXISTS core.salary_offers (
  vacancy_id text PRIMARY KEY REFERENCES core.vacancies(vacancy_id),
  from_raw numeric,
  to_raw numeric,
  currency_raw text,
  gross_raw boolean,
  from_rub numeric,
  to_rub numeric,
  midpoint_rub numeric,
  is_gross boolean,
  normalization_status text NOT NULL,
  assumptions jsonb NOT NULL DEFAULT '{}'::jsonb,
  CHECK (from_rub IS NULL OR from_rub >= 0),
  CHECK (to_rub IS NULL OR to_rub >= 0),
  CHECK (from_rub IS NULL OR to_rub IS NULL OR from_rub <= to_rub)
);

CREATE TABLE IF NOT EXISTS ml.model_versions (
  model_version text PRIMARY KEY,
  target text NOT NULL,
  algorithm text NOT NULL,
  trained_at timestamptz NOT NULL,
  dataset_version text NOT NULL,
  feature_hash text NOT NULL,
  metrics jsonb NOT NULL,
  artifact_path text,
  status text NOT NULL
);

CREATE TABLE IF NOT EXISTS ml.predictions (
  vacancy_id text NOT NULL REFERENCES core.vacancies(vacancy_id),
  target text NOT NULL,
  predicted_class text NOT NULL,
  confidence numeric NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  class_probabilities jsonb NOT NULL DEFAULT '{}'::jsonb,
  model_version text REFERENCES ml.model_versions(model_version),
  rules_version text,
  decision_path text NOT NULL,
  predicted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (vacancy_id, target, model_version, rules_version)
);

CREATE TABLE IF NOT EXISTS ml.seniority_scores (
  vacancy_id text PRIMARY KEY REFERENCES core.vacancies(vacancy_id),
  score numeric NOT NULL,
  explicit_experience numeric NOT NULL,
  title_signal numeric NOT NULL,
  responsibility_signal numeric NOT NULL,
  bucket text NOT NULL,
  rules_version text NOT NULL,
  explanation jsonb NOT NULL
);

CREATE OR REPLACE VIEW mart.vacancy_current AS
SELECT
  publication.snapshot_date AS as_of_date,
  vacancy.vacancy_id,
  vacancy.name_raw,
  vacancy.area_id,
  vacancy.area_name,
  vacancy.published_at,
  vacancy.alternate_url,
  publication.is_active,
  publication.is_representative,
  prediction.predicted_class AS role,
  seniority.bucket AS seniority,
  salary.midpoint_rub
FROM core.publications AS publication
JOIN core.vacancies AS vacancy ON vacancy.vacancy_id = publication.vacancy_id
LEFT JOIN LATERAL (
  SELECT predicted_class FROM ml.predictions AS prediction_history
  WHERE prediction_history.vacancy_id = vacancy.vacancy_id
    AND prediction_history.target = 'role'
  ORDER BY predicted_at DESC LIMIT 1
) AS prediction ON true
LEFT JOIN ml.seniority_scores AS seniority ON seniority.vacancy_id = vacancy.vacancy_id
LEFT JOIN core.salary_offers AS salary ON salary.vacancy_id = vacancy.vacancy_id
WHERE publication.is_active AND publication.is_representative;
