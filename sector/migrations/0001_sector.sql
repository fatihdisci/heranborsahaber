-- Separate SECTOR database only. Never apply to former Her An Borsa bindings.
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, config TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
 next_poll INTEGER NOT NULL DEFAULT 0, lease_until INTEGER NOT NULL DEFAULT 0,
 etag TEXT, modified TEXT, failures INTEGER NOT NULL DEFAULT 0,
 last_ok INTEGER, last_error TEXT, last_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS articles (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), url TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL, summary TEXT NOT NULL, published_at TEXT NOT NULL, first_seen INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'queued', document TEXT, document_expires INTEGER,
 next_try INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0, lease_until INTEGER NOT NULL DEFAULT 0,
 error TEXT, draft_id TEXT
);
CREATE INDEX IF NOT EXISTS articles_queue ON articles(status,next_try,published_at);
CREATE TABLE IF NOT EXISTS drafts (
 id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
 content TEXT NOT NULL, documents TEXT NOT NULL, verification TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending', revision INTEGER NOT NULL DEFAULT 1,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, defer_until INTEGER,
 message_id INTEGER, delivered_at INTEGER, delivery_state TEXT NOT NULL DEFAULT 'waiting',
 delivery_attempts INTEGER NOT NULL DEFAULT 0, next_delivery INTEGER NOT NULL DEFAULT 0,
 media_key TEXT, lease_until INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS actions (
 update_id INTEGER PRIMARY KEY, draft_id TEXT, action TEXT NOT NULL, actor TEXT NOT NULL,
 created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS edits (user_id TEXT PRIMARY KEY,draft_id TEXT NOT NULL,revision INTEGER NOT NULL,expires_at INTEGER NOT NULL,prompt_message_id INTEGER);
CREATE TABLE IF NOT EXISTS publication_log (
 id TEXT PRIMARY KEY,draft_id TEXT NOT NULL,revision INTEGER NOT NULL,target TEXT NOT NULL,
 status TEXT NOT NULL,created_at INTEGER NOT NULL,remote_id TEXT,
 UNIQUE(draft_id,revision,target)
);
CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_jobs (
 id TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES articles(id), documents TEXT NOT NULL,
 related_ids TEXT NOT NULL DEFAULT '[]', input_hash TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
 lease_token TEXT, lease_until INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
 result_draft TEXT, error TEXT, kind TEXT NOT NULL DEFAULT 'initial', draft_id TEXT,
 expected_revision INTEGER NOT NULL DEFAULT 0, edit_request TEXT, UNIQUE(article_id,expected_revision)
);
-- Owner-submitted URLs, PDFs and text. Independent of automatic source filtering.
CREATE TABLE IF NOT EXISTS manual_requests (
 update_id INTEGER PRIMARY KEY,message_id INTEGER NOT NULL,kind TEXT NOT NULL,input TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'queued',created_at INTEGER NOT NULL,lease_until INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0,job_id TEXT,error TEXT,notified INTEGER NOT NULL DEFAULT 0
);
-- News previews never reserve model quota. Only an authenticated button click does.
CREATE TABLE IF NOT EXISTS news_cards (
 id TEXT PRIMARY KEY,article_id TEXT NOT NULL UNIQUE REFERENCES articles(id),
 state TEXT NOT NULL DEFAULT 'waiting',message_id INTEGER,created_at INTEGER NOT NULL,
 requested_at INTEGER,next_try INTEGER NOT NULL DEFAULT 0,parent_id TEXT REFERENCES news_cards(id)
);
CREATE INDEX IF NOT EXISTS news_cards_state ON news_cards(state,requested_at);
-- Local render work is separate from model jobs and consumes no AI calls.
CREATE TABLE IF NOT EXISTS card_redesigns (
 update_id INTEGER PRIMARY KEY,draft_id TEXT NOT NULL REFERENCES drafts(id),
 revision INTEGER NOT NULL,message_id INTEGER NOT NULL,layout TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'queued',created_at INTEGER NOT NULL,lease_until INTEGER NOT NULL DEFAULT 0,error TEXT
);
CREATE INDEX IF NOT EXISTS card_redesigns_state ON card_redesigns(state,created_at);
CREATE UNIQUE INDEX IF NOT EXISTS card_redesigns_active ON card_redesigns(draft_id) WHERE state IN ('queued','rendering');
