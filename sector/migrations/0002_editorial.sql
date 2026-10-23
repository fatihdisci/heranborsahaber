-- Additive editor migration; no existing source, queue or delivery row is rewritten.
CREATE TABLE IF NOT EXISTS news_candidates (
 id TEXT PRIMARY KEY,article_id TEXT NOT NULL,url TEXT NOT NULL UNIQUE,source_id TEXT NOT NULL,
 title TEXT NOT NULL,summary TEXT NOT NULL,published_at TEXT,first_seen INTEGER NOT NULL,expires_at INTEGER NOT NULL,
 route TEXT NOT NULL,reasons TEXT NOT NULL,confidence TEXT NOT NULL,rule_version TEXT NOT NULL,evaluated_at INTEGER NOT NULL,
 legacy_eligible INTEGER NOT NULL,eligible INTEGER NOT NULL,signature TEXT NOT NULL,event_group TEXT NOT NULL,suggestions TEXT NOT NULL DEFAULT '[]',family TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS news_candidates_route ON news_candidates(route,eligible,evaluated_at);
CREATE TABLE IF NOT EXISTS news_feedback (update_id INTEGER PRIMARY KEY,candidate_id TEXT NOT NULL,kind TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS news_digest_runs (id TEXT PRIMARY KEY,state TEXT NOT NULL,created_at INTEGER NOT NULL,message_id INTEGER,error TEXT,items TEXT NOT NULL DEFAULT '[]',attempts INTEGER NOT NULL DEFAULT 0,next_try INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS editor_corrections (update_id INTEGER PRIMARY KEY,draft_id TEXT NOT NULL,revision INTEGER NOT NULL,path TEXT NOT NULL,before_value TEXT NOT NULL,after_value TEXT NOT NULL,unit TEXT,period TEXT,created_at INTEGER NOT NULL,state TEXT NOT NULL DEFAULT 'proposed');
CREATE TABLE IF NOT EXISTS editor_prompts (user_id TEXT PRIMARY KEY,draft_id TEXT NOT NULL,revision INTEGER NOT NULL,message_id INTEGER NOT NULL,kind TEXT NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS publication_snapshots (id TEXT PRIMARY KEY,draft_id TEXT NOT NULL,revision INTEGER NOT NULL,published_at INTEGER NOT NULL,method TEXT NOT NULL,text TEXT NOT NULL,content TEXT NOT NULL,source_urls TEXT NOT NULL,media_key TEXT NOT NULL,media_hash TEXT,remote_url TEXT,created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS publication_snapshots_draft ON publication_snapshots(draft_id,method,published_at);

CREATE INDEX IF NOT EXISTS news_candidates_evaluated ON news_candidates(evaluated_at);
CREATE UNIQUE INDEX IF NOT EXISTS news_candidates_article ON news_candidates(article_id);
CREATE INDEX IF NOT EXISTS news_candidates_group ON news_candidates(event_group);
CREATE INDEX IF NOT EXISTS news_candidates_expiry ON news_candidates(expires_at);
CREATE TABLE IF NOT EXISTS news_event_links (child_id TEXT NOT NULL,parent_id TEXT NOT NULL,actor TEXT NOT NULL,created_at INTEGER NOT NULL,PRIMARY KEY(child_id,parent_id));

CREATE UNIQUE INDEX IF NOT EXISTS publication_snapshots_event ON publication_snapshots(draft_id,method,published_at);
