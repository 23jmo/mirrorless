-- Calendar events scraped from Google Calendar API.
-- Uses ON CONFLICT DO UPDATE (not DO NOTHING) because event details change after creation.

CREATE TABLE calendar_events (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  google_event_id text NOT NULL,
  title           text NOT NULL,
  start_time      timestamptz NOT NULL,
  end_time        timestamptz,
  location        text,
  description     text,
  attendee_count  integer DEFAULT 0,
  is_all_day      boolean DEFAULT false,
  status          text,
  scraped_at      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_calendar_events_user_google_id ON calendar_events(user_id, google_event_id);
CREATE INDEX idx_calendar_events_user_start ON calendar_events(user_id, start_time);
