-- Apply after the base analysis_jobs schema in infra/init.sql.
CREATE TABLE IF NOT EXISTS research_papers (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  extracted_text TEXT NOT NULL,
  method_json JSONB NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (job_id, sha256)
);

CREATE TABLE IF NOT EXISTS paper_adaptations (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  paper_ids JSONB NOT NULL,
  instruction TEXT NOT NULL,
  source_dataset TEXT,
  target_dataset TEXT,
  parameter_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
  recommendation_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
