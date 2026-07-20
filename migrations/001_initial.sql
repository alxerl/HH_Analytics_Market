CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
  run_id uuid PRIMARY KEY,
  pipeline_name text NOT NULL,
  snapshot_date date NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status text NOT NULL CHECK (status IN ('started', 'partial', 'succeeded', 'failed')),
  code_version text NOT NULL,
  config_hash text NOT NULL,
  error_summary text,
  attempt_no integer NOT NULL DEFAULT 1 CHECK (attempt_no > 0)
);

CREATE TABLE IF NOT EXISTS raw.api_requests (
  request_id uuid PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
  query_id text NOT NULL,
  area_id integer NOT NULL,
  page_no integer NOT NULL CHECK (page_no >= 0),
  request_params jsonb NOT NULL,
  http_status integer,
  requested_at timestamptz NOT NULL,
  received_at timestamptz,
  items_count integer,
  found_count integer,
  raw_path text,
  sha256 text,
  status text NOT NULL CHECK (status IN ('started', 'succeeded', 'failed')),
  UNIQUE (run_id, query_id, area_id, page_no)
);

CREATE TABLE IF NOT EXISTS raw.vacancy_snapshots (
  snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
  vacancy_id text NOT NULL,
  snapshot_at timestamptz NOT NULL,
  payload jsonb NOT NULL,
  payload_hash text NOT NULL,
  source_request_id uuid NOT NULL REFERENCES raw.api_requests(request_id),
  UNIQUE (vacancy_id, snapshot_at, payload_hash)
);

CREATE TABLE IF NOT EXISTS core.employers (
  employer_id text PRIMARY KEY,
  name text,
  normalized_name text,
  url text,
  trusted boolean,
  first_seen_at timestamptz NOT NULL,
  last_seen_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS core.vacancies (
  vacancy_id text PRIMARY KEY,
  employer_id text REFERENCES core.employers(employer_id),
  name_raw text NOT NULL,
  name_normalized text NOT NULL,
  description_html text,
  description_text text,
  area_id integer,
  area_name text,
  published_at timestamptz,
  created_at timestamptz,
  archived_at timestamptz,
  experience_code text,
  employment_code text,
  schedule_code text,
  accept_temporary boolean,
  alternate_url text,
  first_seen_at timestamptz NOT NULL,
  last_seen_at timestamptz NOT NULL,
  content_hash text NOT NULL
);

CREATE TABLE IF NOT EXISTS core.publications (
  publication_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  vacancy_id text NOT NULL REFERENCES core.vacancies(vacancy_id),
  snapshot_date date NOT NULL,
  published_at timestamptz,
  content_hash text NOT NULL,
  is_active boolean NOT NULL,
  source_snapshot_id bigint NOT NULL REFERENCES raw.vacancy_snapshots(snapshot_id),
  duplicate_cluster_id uuid,
  is_representative boolean NOT NULL DEFAULT false,
  UNIQUE (vacancy_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS ix_publications_date_active ON core.publications(snapshot_date, is_active);
CREATE INDEX IF NOT EXISTS ix_api_requests_received ON raw.api_requests(received_at);
