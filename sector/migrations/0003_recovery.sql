-- Durable incoming Telegram queue and per-update outgoing-effect receipts.
-- Terminal updates keep status/error metadata, not the user's message payload.
CREATE TABLE IF NOT EXISTS telegram_updates (
 update_id INTEGER PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'queued',
 attempts INTEGER NOT NULL DEFAULT 0,next_try INTEGER NOT NULL DEFAULT 0,
 lease_until INTEGER NOT NULL DEFAULT 0,error TEXT,created_at INTEGER NOT NULL,finished_at INTEGER
);
CREATE INDEX IF NOT EXISTS telegram_updates_due ON telegram_updates(state,next_try,update_id);
CREATE TABLE IF NOT EXISTS telegram_effects (
 id TEXT PRIMARY KEY,update_id INTEGER NOT NULL,method TEXT NOT NULL,state TEXT NOT NULL,
 result TEXT,error_code INTEGER,updated_at INTEGER NOT NULL
);
