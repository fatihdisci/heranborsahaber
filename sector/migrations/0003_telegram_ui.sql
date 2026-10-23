-- Telegram UI: independent owner interests; existing detailed feedback and routes remain untouched.
CREATE TABLE IF NOT EXISTS news_interests (actor TEXT NOT NULL,article_id TEXT NOT NULL,candidate_id TEXT,source_id TEXT NOT NULL,choice TEXT CHECK(choice IN ('like','dislike') OR choice IS NULL),update_id INTEGER NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(actor,article_id));
CREATE TABLE IF NOT EXISTS news_interest_actions (update_id INTEGER PRIMARY KEY,actor TEXT NOT NULL,article_id TEXT NOT NULL,choice TEXT NOT NULL,created_at INTEGER NOT NULL);
