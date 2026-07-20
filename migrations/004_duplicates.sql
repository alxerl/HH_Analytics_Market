CREATE TABLE IF NOT EXISTS core.duplicate_clusters (
  cluster_id uuid PRIMARY KEY,
  method text NOT NULL,
  threshold numeric NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  algorithm_version text NOT NULL
);

CREATE TABLE IF NOT EXISTS core.duplicate_cluster_members (
  cluster_id uuid NOT NULL REFERENCES core.duplicate_clusters(cluster_id),
  publication_id bigint NOT NULL REFERENCES core.publications(publication_id),
  similarity numeric NOT NULL CHECK (similarity >= 0 AND similarity <= 1),
  is_representative boolean NOT NULL DEFAULT false,
  PRIMARY KEY (cluster_id, publication_id)
);

CREATE INDEX IF NOT EXISTS ix_duplicate_members_publication
  ON core.duplicate_cluster_members(publication_id);
