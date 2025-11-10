# ETL Scripts

This directory contains ETL (Extract, Transform, Load) scripts for loading democracy data into the database.

## Available Data Sources

### 1. Freedom House - Freedom in the World (Annual)
**Script:** `load_freedom_house.py`
**Update Frequency:** Annual (typically January)
**Metrics:**
- Political Rights (0-100 scale)
- Civil Liberties (0-100 scale)
- Freedom Score (average of PR and CL)

**Usage:**
```bash
python etl/load_freedom_house.py
```

**Data Coverage:** 195+ countries, 1972-present

---

### 2. World Bank - Worldwide Governance Indicators (Annual)
**Script:** `load_world_bank_wgi.py`
**Update Frequency:** Annual (typically mid-year)
**Metrics:**
- Voice and Accountability
- Political Stability and Absence of Violence
- Government Effectiveness
- Regulatory Quality
- Rule of Law
- Control of Corruption

**Usage:**
```bash
python etl/load_world_bank_wgi.py
```

**Data Coverage:** 214 economies, 1996-present

---

## Running ETL Scripts

### Prerequisites
- Python 3.8+
- PostgreSQL database configured (see `.env.example`)
- Required environment variables in `.env` file

### Manual Execution
Run individual scripts:
```bash
python etl/load_freedom_house.py
python etl/load_world_bank_wgi.py
```

### Automated Execution
ETL scripts run automatically via GitHub Actions:
- **Daily at 6:00 AM UTC:** Freedom House, World Bank WGI

See `.github/workflows/etl.yml` for configuration.

---

## Database Schema

### Metrics Table (Annual Data)
Stores time-series metrics (Freedom House, WGI):
```sql
metrics (
  id BIGSERIAL PRIMARY KEY,
  country_id INT REFERENCES countries(id),
  metric_name TEXT,
  metric_value DOUBLE PRECISION,
  source TEXT,
  date DATE
)
```

### Events Table (Real-Time Data)
Stores democracy events:
```sql
events (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT UNIQUE,
  country_id INT REFERENCES countries(id),
  event_date DATE,
  event_type TEXT,
  sub_event_type TEXT,
  disorder_type TEXT,
  actor1 TEXT,
  actor2 TEXT,
  fatalities INT,
  notes TEXT,
  location_name TEXT,
  admin1, admin2, admin3 TEXT,
  latitude, longitude DOUBLE PRECISION,
  source TEXT,
  source_url TEXT,
  created_at TIMESTAMP
)
```

---

## Adding New Data Sources

To add a new data source:

1. **Create ETL script:** `etl/load_<source>.py`
2. **Follow existing patterns:**
   - Use environment variables for credentials
   - Use SQLAlchemy with connection string
   - Implement upsert logic (insert or update)
   - Print progress and statistics
3. **Update schema if needed:** Add to `schema.sql` or create migration
4. **Document:** Update this README
5. **Automate:** Add to `.github/workflows/etl.yml`

---

## Troubleshooting

### Connection Errors
- Verify `.env` file has correct database credentials
- Check database is accessible (Neon requires SSL: `?sslmode=require`)

### No Data Loaded
- Check script output for country mapping issues
- Verify countries exist in `countries` table

---

## Data Retention

- **Metrics:** Kept indefinitely (annual data, small volume)
- **Events:** Currently kept indefinitely
  - Future: May implement retention policy (e.g., keep last 2 years) if storage fills

Current database size: ~2,800 metrics + events (well within Neon free tier 512MB limit)
