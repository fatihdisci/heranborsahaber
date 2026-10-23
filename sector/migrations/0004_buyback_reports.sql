-- Independent report receipts, using the existing drafts/delivery/publication ledgers.
CREATE TABLE IF NOT EXISTS buyback_reports (
 id TEXT PRIMARY KEY,url TEXT NOT NULL,image_url TEXT NOT NULL,image_hash TEXT NOT NULL,
 published_at TEXT NOT NULL,day TEXT,semantic_hash TEXT,state TEXT NOT NULL,
 result_draft TEXT,error TEXT,evidence TEXT,created_at INTEGER NOT NULL,lease_until INTEGER NOT NULL DEFAULT 0,
 UNIQUE(url,image_hash)
);
CREATE TABLE IF NOT EXISTS buyback_days (
 day TEXT PRIMARY KEY,producer TEXT NOT NULL,draft_id TEXT NOT NULL,version TEXT NOT NULL
);
