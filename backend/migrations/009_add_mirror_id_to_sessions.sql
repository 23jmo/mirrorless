-- 009_add_mirror_id_to_sessions.sql
-- Add mirror_id column to sessions table for mirror-based session lookup.
-- Also make user_id nullable for mirror-only sessions (Poke-driven, no user account).

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS mirror_id text;
CREATE INDEX IF NOT EXISTS idx_sessions_mirror_id ON sessions(mirror_id) WHERE mirror_id IS NOT NULL;

ALTER TABLE sessions ALTER COLUMN user_id DROP NOT NULL;
