-- Existing D1 installations have already applied 0001. Local SQLite also
-- includes this idempotent table in its bootstrap schema.
CREATE TABLE IF NOT EXISTS model_reviews (
 job_id TEXT PRIMARY KEY REFERENCES model_jobs(id), issues TEXT NOT NULL DEFAULT '[]',
 retries INTEGER NOT NULL DEFAULT 0, next_retry INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL
);
