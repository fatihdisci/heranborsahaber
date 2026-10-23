-- Minimal editor audit metadata, no full article or source body. Votes remain untouched.
CREATE TABLE IF NOT EXISTS news_interest_context (
 actor TEXT NOT NULL, article_id TEXT NOT NULL, title TEXT, url TEXT, source_id TEXT,
 saved_at INTEGER NOT NULL, provenance TEXT NOT NULL, PRIMARY KEY(actor,article_id)
);
CREATE TABLE IF NOT EXISTS news_interest_snapshots (
 update_id INTEGER PRIMARY KEY, actor TEXT NOT NULL, article_id TEXT NOT NULL,
 result_choice TEXT, decision TEXT, captured_at INTEGER NOT NULL
);
-- A lookup today cannot reconstruct the decision when a legacy button was pressed.
INSERT OR IGNORE INTO news_interest_context(actor,article_id,title,url,source_id,saved_at,provenance)
 SELECT i.actor,i.article_id,COALESCE(a.title,(SELECT title FROM news_candidates WHERE article_id=i.article_id ORDER BY evaluated_at DESC LIMIT 1)),COALESCE(a.url,(SELECT url FROM news_candidates WHERE article_id=i.article_id ORDER BY evaluated_at DESC LIMIT 1)),i.source_id,CAST(strftime('%s','now') AS INTEGER)*1000,'migration_lookup'
 FROM news_interests i LEFT JOIN articles a ON a.id=i.article_id;
