-- 007_add_is_fashion.sql
-- Add is_fashion boolean to purchases table for filtering fashion vs non-fashion items.
-- Existing rows default to true (they were already fashion-filtered at scrape time).

ALTER TABLE purchases
  ADD COLUMN IF NOT EXISTS is_fashion boolean NOT NULL DEFAULT true;

-- Partial index for fast fashion-filtered queries
CREATE INDEX IF NOT EXISTS idx_purchases_is_fashion
  ON purchases(user_id, is_fashion) WHERE is_fashion = true;

-- Backfill: mark known non-fashion brands as false
UPDATE purchases SET is_fashion = false
WHERE LOWER(brand) IN (
  'github', 'google', 'robinhood', 'supabase', 'medium', 'reddit',
  'starbucks', 'uber', 'lyft', 'doordash', 'grubhub', 'venmo',
  'paypal', 'cashapp', 'wise', 'stripe', 'anthropic', 'openai',
  'vercel', 'netlify', 'heroku', 'aws', 'azure', 'lovable',
  'bakedbymelissa', 'slack', 'notion', 'figma', 'linear'
);
