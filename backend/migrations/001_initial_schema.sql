-- 001_initial_schema.sql
-- Creates all tables for the Mirrorless application

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  email text UNIQUE NOT NULL,
  phone text,
  google_oauth_token jsonb,
  poke_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE style_profiles (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  brands text[] DEFAULT '{}',
  price_range jsonb,
  style_tags text[] DEFAULT '{}',
  size_info jsonb,
  narrative_summary text
);

CREATE TABLE purchases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand text NOT NULL,
  item_name text NOT NULL,
  category text,
  price numeric,
  date date,
  source_email_id text
);

CREATE TABLE sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned'))
);

CREATE TABLE clothing_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  brand text,
  price numeric,
  image_url text,
  buy_url text,
  category text,
  source text DEFAULT 'serpapi'
);

CREATE TABLE session_outfits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  outfit_data jsonb NOT NULL DEFAULT '{}',
  reaction text CHECK (reaction IN ('liked', 'disliked', 'skipped')),
  clothing_items uuid[] DEFAULT '{}'
);

CREATE TABLE queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  position integer NOT NULL,
  status text NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'active', 'completed')),
  joined_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_purchases_user_id ON purchases(user_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_session_outfits_session_id ON session_outfits(session_id);
CREATE INDEX idx_queue_status ON queue(status);
CREATE INDEX idx_queue_position ON queue(position);
