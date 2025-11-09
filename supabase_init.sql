-- Democracy Lens - Complete Database Initialization Script
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/mgnvookdlrxklhiczxjw/sql

-- ============================================================
-- Step 1: Create Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS countries (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  iso_code CHAR(3) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
  id BIGSERIAL PRIMARY KEY,
  country_id INT NOT NULL REFERENCES countries(id),
  metric_name TEXT NOT NULL,
  metric_value DOUBLE PRECISION NOT NULL,
  source TEXT,
  date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS metrics_country_metric_date_idx
  ON metrics (country_id, metric_name, date);

-- ============================================================
-- Step 2: Seed Initial Countries
-- ============================================================

INSERT INTO countries (name, iso_code) VALUES
  ('United States', 'USA'),
  ('United Kingdom', 'GBR'),
  ('Germany', 'DEU'),
  ('France', 'FRA'),
  ('Japan', 'JPN'),
  ('Canada', 'CAN'),
  ('Australia', 'AUS'),
  ('India', 'IND'),
  ('Brazil', 'BRA'),
  ('South Africa', 'ZAF'),
  ('Mexico', 'MEX'),
  ('Argentina', 'ARG'),
  ('South Korea', 'KOR'),
  ('Poland', 'POL'),
  ('Spain', 'ESP')
ON CONFLICT (iso_code) DO NOTHING;

-- ============================================================
-- Step 3: Create Read-Only User for Streamlit App
-- ============================================================

-- Create read-only role (if it doesn't exist)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_read') THEN
    CREATE ROLE app_read WITH LOGIN PASSWORD 'SecureReadOnlyPass2024!';
  END IF;
END
$$;

-- Grant permissions
GRANT CONNECT ON DATABASE postgres TO app_read;
GRANT USAGE ON SCHEMA public TO app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;

-- ============================================================
-- Verification
-- ============================================================

-- Check results
SELECT 'Countries created:' AS status, COUNT(*)::text AS count FROM countries
UNION ALL
SELECT 'Metrics created:', COUNT(*)::text FROM metrics
UNION ALL
SELECT 'Index exists:', CASE WHEN EXISTS (
  SELECT 1 FROM pg_indexes
  WHERE tablename = 'metrics'
  AND indexname = 'metrics_country_metric_date_idx'
) THEN 'Yes' ELSE 'No' END;

-- List all countries
SELECT * FROM countries ORDER BY name;
