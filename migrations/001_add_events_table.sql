-- Migration: Add events table for real-time democracy events
-- Date: 2025-01-09
-- Description: Creates events table to store real-time democracy events

-- Events table for real-time democracy events
CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT UNIQUE NOT NULL,
  country_id INT NOT NULL REFERENCES countries(id),
  event_date DATE NOT NULL,
  event_type TEXT NOT NULL,
  sub_event_type TEXT,
  disorder_type TEXT,
  actor1 TEXT,
  actor2 TEXT,
  fatalities INT DEFAULT 0,
  notes TEXT,
  location_name TEXT,
  admin1 TEXT,
  admin2 TEXT,
  admin3 TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  source TEXT NOT NULL,
  source_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS events_country_date_idx
  ON events (country_id, event_date DESC);

CREATE INDEX IF NOT EXISTS events_type_date_idx
  ON events (event_type, event_date DESC);

CREATE INDEX IF NOT EXISTS events_source_idx
  ON events (source, event_date DESC);
