-- Migration 010: Phone number constraints and indexing
-- Purpose: Optimize phone lookups for Poke MCP integration

-- Add index for phone lookups (improves MCP server performance)
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone) WHERE phone IS NOT NULL;

-- Optional: Add unique constraint (uncomment only after confirming no duplicate test data)
-- This ensures each phone number can only be associated with one user account
-- ALTER TABLE users ADD CONSTRAINT uq_users_phone UNIQUE (phone);

-- Note: Run this migration after phone collection is deployed to production
-- to ensure optimal performance for get_past_sessions MCP tool queries.
