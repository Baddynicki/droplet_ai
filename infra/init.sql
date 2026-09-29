-- Enable pgvector (should already be available in this image, but harmless to ensure)
CREATE EXTENSION IF NOT EXISTS vector;

-- Basic tables for MVP

--analysis jobs table
CREATE TABLE IF NOT EXISTS analysis_jobs (
  id UUID PRIMARY KEY,
  repo_url TEXT NOT NULL,
  branch TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

--history events table
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


--method schema 
CREATE TABLE IF NOT EXISTS method_schemas (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  repo_url TEXT NOT NULL,
  branch TEXT NOT NULL,
  schema_yaml TEXT NOT NULL,
  schema_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


--code structures table
CREATE TABLE IF NOT EXISTS code_structures (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  repo_url TEXT NOT NULL,
  branch TEXT NOT NULL,
  structure_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Uploaded research papers and their LLM-extracted machine-readable method.
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

-- Adaptations stay traceable to their source papers and user requirements.
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
