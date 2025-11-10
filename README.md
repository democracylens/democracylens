# Democracy Lens

A public, non-partisan data dashboard tracking democracy and governance indicators across countries.

**Live site:** [democracylens.com](https://democracylens.com)

## Overview

Democracy Lens makes global democracy data accessible, factual, and easy to explore. The dashboard presents democratic health metrics from authoritative sources including Freedom House and the World Bank's Worldwide Governance Indicators.

**Design Principles:**
- Non-partisan, neutral presentation
- Data-driven with no commentary or advocacy
- Lightweight and fully hosted on free-tier services
- Privacy-respecting (no analytics or tracking)
- Open-source and transparent

## Tech Stack

- **Frontend:** Streamlit (hosted on Streamlit Community Cloud)
- **Database:** PostgreSQL on Neon (free tier)
- **ETL:** Python scripts via GitHub Actions (nightly)
- **Cost:** $0/month for MVP

## Project Structure

```
democracylens/
├── app.py                          # Streamlit dashboard
├── init_db.py                      # Database initialization script
├── schema.sql                      # Database schema
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── etl/
│   ├── load_freedom_house.py      # Freedom House ETL script
│   └── data/
│       └── freedom_house_sample.csv
└── .github/
    └── workflows/
        └── etl.yml                 # Nightly ETL job
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL database (Neon recommended)
- Git

### 1. Clone Repository

```bash
git clone https://github.com/your-org/democracylens.git
cd democracylens
```

### 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your database credentials:

```bash
cp .env.example .env
```

**For Neon Database:**

Get your credentials from: Neon Console → Dashboard → Connection Details

```env
DB_HOST=ep-your-endpoint.region.aws.neon.tech  # From connection string
DB_PORT=5432
DB_NAME=neondb                        # Default database name
DB_USER=app_read                      # Read-only user (create after init)
DB_PASSWORD=your-readonly-password
DB_ADMIN_USER=neondb_owner            # Default admin user
DB_ADMIN_PW=your-neon-password        # From project settings
```

### 4. Initialize Database

Run the initialization script to apply schema and seed country data:

```bash
python init_db.py
```

This will:
- Create `countries` and `metrics` tables
- Add indexes for query performance
- Seed 15 initial countries

### 5. Load Sample Data

Run the ETL script to load Freedom House metrics:

```bash
python etl/load_freedom_house.py
```

### 6. Run the App Locally

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## Database Schema

### countries

| Column   | Type    | Description |
|----------|---------|-------------|
| id       | SERIAL  | Primary key |
| name     | TEXT    | Country name |
| iso_code | CHAR(3) | ISO 3166-1 alpha-3 code |

### metrics

| Column       | Type             | Description |
|--------------|------------------|-------------|
| id           | BIGSERIAL        | Primary key |
| country_id   | INT              | Foreign key to countries |
| metric_name  | TEXT             | Name of the metric |
| metric_value | DOUBLE PRECISION | Numeric value |
| source       | TEXT             | Data source (e.g., "Freedom House") |
| date         | DATE             | Measurement date |

**Index:** `metrics_country_metric_date_idx` on (country_id, metric_name, date)

## Deployment

### Streamlit Community Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Configure secrets (add DB_* variables)
5. Deploy

### Custom Domain Setup

1. Register domain with WHOIS privacy enabled
2. In Streamlit Cloud settings:
   - Go to Settings → General → Custom domain
   - Add your domain (e.g., democracylens.com)
3. Update DNS records as instructed by Streamlit

### GitHub Actions Setup

The ETL workflow runs nightly at 3:17 AM UTC.

**Required GitHub Secrets:**
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_ADMIN_USER`
- `DB_ADMIN_PW`

To configure:
1. Go to repository Settings → Secrets → Actions
2. Add each secret with your Neon database credentials

## Development

### Git Configuration (Anonymous Commits)

To maintain project anonymity:

```bash
git config user.name "Democracy Lens Project"
git config user.email "noreply@democracylens.com"
```

Use the provided `.gitmessage` template:

```bash
git config commit.template .gitmessage
```

### Adding New Data Sources

1. Create a new ETL script in `etl/` directory
2. Follow the pattern from `load_freedom_house.py`
3. Add CSV data to `etl/data/`
4. Update GitHub Actions workflow if needed

### Local Testing

Run the ETL script locally to test before deployment:

```bash
python etl/load_freedom_house.py
```

Check logs for errors and verify data in the database.

## Data Sources

- **Freedom House** - Freedom in the World annual survey (1972-present)
  - Political Rights, Civil Liberties, Freedom Score
  - 195+ countries, updated annually
- **World Bank WGI** - Worldwide Governance Indicators (1996-present)
  - Voice & Accountability, Political Stability, Government Effectiveness
  - Regulatory Quality, Rule of Law, Control of Corruption
  - 214 economies, updated annually

All data sources are free, open, and automatically updated nightly via GitHub Actions.

## Privacy & Security

- **Read-only access:** The Streamlit app uses a read-only database user
- **No tracking:** No analytics, cookies, or user data collection
- **Anonymity:** Project maintained with generic identity
- **Open source:** All code is public and auditable

## Contributing

This project maintains strict anonymity requirements. Contributions must:
- Use generic/anonymous identity
- Not include personal information
- Follow non-partisan, neutral presentation guidelines

## License

[License information to be added]

## Contact

For questions or issues, please open a GitHub issue.
