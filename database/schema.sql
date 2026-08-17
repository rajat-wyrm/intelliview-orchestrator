CREATE TABLE IF NOT EXISTS subscribers (
    webhook_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    secret_ref TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TEXT
);