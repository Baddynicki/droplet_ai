-- Enable pgvector (should already be available in this image, but harmless to ensure)
CREATE EXTENSION IF NOT EXISTS vector;

-- Basic tables for MVP

CREATE TABLE IF NOT EXISTS analysis_jobs (
  id UUID PRIMARY KEY,
  repo_url TEXT NOT NULL,
  branch TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS history_events (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  commit_id TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  files_touched JSONB NOT NULL,
  diff_summary JSONB NOT NULL,
  llm_summary JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS method_schemas (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  repo_url TEXT NOT NULL,
  branch TEXT NOT NULL,
  schema_yaml TEXT NOT NULL,
  schema_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);