-- Add selfie storage column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS selfie_base64 TEXT;
