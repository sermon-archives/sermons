CREATE TABLE IF NOT EXISTS sermons (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, published_at TEXT, url TEXT NOT NULL,
  description TEXT DEFAULT '', summary TEXT DEFAULT '', outline TEXT DEFAULT '', devotional_questions TEXT DEFAULT '', duration_seconds INTEGER, is_sermon INTEGER NOT NULL DEFAULT 0,
  classification_reason TEXT DEFAULT '', transcript TEXT DEFAULT '',
  transcript_engine TEXT DEFAULT '', transcript_status TEXT NOT NULL DEFAULT 'pending',
  strengths TEXT DEFAULT '', weaknesses TEXT DEFAULT '', review_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS sermons_published_idx ON sermons(published_at DESC);

CREATE TABLE IF NOT EXISTS transcription_queue (
  sermon_id TEXT PRIMARY KEY REFERENCES sermons(id), priority INTEGER NOT NULL DEFAULT 100,
  status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  available_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, locked_at TEXT, last_error TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS queue_ready_idx ON transcription_queue(status, priority, available_at);
