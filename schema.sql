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
