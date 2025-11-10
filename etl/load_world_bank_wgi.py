"""
ETL script to load World Bank Worldwide Governance Indicators (WGI) into the database.
Uses the World Bank Data API (no authentication required).

WGI covers 6 dimensions of governance for 200+ countries from 1996-2023:
- Voice and Accountability
- Political Stability and Absence of Violence
- Government Effectiveness
- Regulatory Quality
- Rule of Law
- Control of Corruption

Data source: https://www.worldbank.org/en/publication/worldwide-governance-indicators
API docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

import os
import time
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(override=True)

# Database connection with SSL
engine = create_engine(
    f"postgresql+psycopg2://{os.environ['DB_ADMIN_USER']}:{os.environ['DB_ADMIN_PW']}@"
    f"{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
    f"?sslmode=require",
    pool_pre_ping=True,
)

# World Bank WGI indicator codes
# Format: (indicator_code, friendly_name)
WGI_INDICATORS = [
    ('CC.EST', 'Control of Corruption'),
    ('GE.EST', 'Government Effectiveness'),
    ('PV.EST', 'Political Stability'),
    ('RQ.EST', 'Regulatory Quality'),
    ('RL.EST', 'Rule of Law'),
    ('VA.EST', 'Voice and Accountability'),
]

# Minimum year (WGI data starts in 1996, but we'll respect the user's floor)
MIN_YEAR = 1960  # WGI only goes back to 1996 anyway

# World Bank API base URL
WB_API_BASE = "https://api.worldbank.org/v2"


def fetch_wgi_indicator(indicator_code, indicator_name):
    """Fetch data for a single WGI indicator from World Bank API."""
    print(f"\n[INFO] Fetching {indicator_name} ({indicator_code})...")

    # API endpoint: get indicator data for all countries
    # Format: json, per_page=20000 to get all data in one call
    url = f"{WB_API_BASE}/country/all/indicator/{indicator_code}"
    params = {
        'format': 'json',
        'per_page': 20000,  # Get all data
        'date': f'{MIN_YEAR}:2030'  # Date range (API will return what's available)
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # World Bank API returns [metadata, data]
        if len(data) < 2 or data[1] is None:
            print(f"[WARNING] No data returned for {indicator_name}")
            return []

        records = data[1]
        print(f"[SUCCESS] Fetched {len(records)} records")

        # Transform to our format
        transformed = []
        for record in records:
            # Skip records with no value
            if record.get('value') is None:
                continue

            # Extract info
            country_code = record.get('countryiso3code')  # ISO 3-letter code
            country_name = record.get('country', {}).get('value', '')
            year = record.get('date')  # Year as string
            value = record.get('value')

            # Skip aggregates (no ISO code)
            if not country_code or len(country_code) != 3:
                continue

            # Convert year to date
            try:
                year_int = int(year)
                if year_int < MIN_YEAR:
                    continue
                date = f"{year}-01-01"
            except (ValueError, TypeError):
                continue

            transformed.append({
                'country_code': country_code,
                'country_name': country_name,
                'metric_name': indicator_name,
                'metric_value': float(value),
                'date': date
            })

        print(f"[INFO] Transformed {len(transformed)} valid records")
        return transformed

    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {indicator_name}: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Error processing {indicator_name}: {e}")
        return []


def normalize_country_name(code, name, country_cache):
    """Match country to database using ISO code or name."""
    # Try ISO code first (most reliable)
    if code in country_cache:
        return country_cache[code]

    # Try name
    if name in country_cache:
        return country_cache[name]

    # Common variations
    variations = {
        'United States': 'United States',
        'United Kingdom': 'United Kingdom',
        'Korea, Rep.': 'South Korea',
        'Korea, Dem. People\'s Rep.': 'North Korea',
    }

    if name in variations and variations[name] in country_cache:
        return country_cache[variations[name]]

    return None


# Main execution
print("=" * 60)
print("World Bank WGI ETL - Governance Indicators Loader")
print("=" * 60)
print(f"Minimum year: {MIN_YEAR}")
print(f"Indicators: {len(WGI_INDICATORS)}")

# Fetch all indicators
all_records = []
for indicator_code, indicator_name in WGI_INDICATORS:
    records = fetch_wgi_indicator(indicator_code, indicator_name)
    all_records.extend(records)
    time.sleep(0.5)  # Be nice to the API

print(f"\n[INFO] Total records fetched: {len(all_records)}")

if not all_records:
    print("[ERROR] No data fetched. Exiting.")
    exit(1)

# Load to database
print("\n[INFO] Loading data to database...")
stats = defaultdict(int)
errors = []

try:
    with engine.begin() as conn:
        # Build country cache
        country_cache = {}
        result = conn.execute(text("SELECT id, name, iso_code FROM countries"))
        for row in result:
            country_cache[row.name] = row.id
            if hasattr(row, 'iso_code') and row.iso_code:
                country_cache[row.iso_code] = row.id

        print(f"   Found {len(country_cache)} countries in database")
        print(f"   Processing {len(all_records)} records...")

        # Process each record
        for idx, record in enumerate(all_records):
            try:
                # Match country
                country_id = normalize_country_name(
                    record['country_code'],
                    record['country_name'],
                    country_cache
                )

                if not country_id:
                    if stats['skipped'] < 5:
                        errors.append(
                            f"Country '{record['country_name']}' ({record['country_code']}) not in database"
                        )
                    stats['skipped'] += 1
                    continue

                # Check if record exists
                check_result = conn.execute(
                    text("""
                        SELECT id FROM metrics
                        WHERE country_id = :country_id
                        AND metric_name = :metric_name
                        AND date = :date
                        AND source = :source
                    """),
                    {
                        'country_id': country_id,
                        'metric_name': record['metric_name'],
                        'date': record['date'],
                        'source': 'World Bank WGI'
                    }
                )
                existing = check_result.fetchone()

                if existing:
                    # Update
                    conn.execute(
                        text("""
                            UPDATE metrics
                            SET metric_value = :metric_value
                            WHERE id = :id
                        """),
                        {
                            'id': existing.id,
                            'metric_value': record['metric_value']
                        }
                    )
                    stats['updated'] += 1
                else:
                    # Insert
                    conn.execute(
                        text("""
                            INSERT INTO metrics (country_id, metric_name, metric_value, source, date)
                            VALUES (:country_id, :metric_name, :metric_value, :source, :date)
                        """),
                        {
                            'country_id': country_id,
                            'metric_name': record['metric_name'],
                            'metric_value': record['metric_value'],
                            'source': 'World Bank WGI',
                            'date': record['date']
                        }
                    )
                    stats['inserted'] += 1

            except Exception as e:
                errors.append(f"Record {idx}: {str(e)}")
                stats['errors'] += 1

        print("[SUCCESS] Transaction committed")

except Exception as e:
    print(f"\n[ERROR] Database error: {e}")
    exit(1)

# Print summary
print("\n" + "=" * 60)
print("ETL Summary")
print("=" * 60)
print(f"  Inserted: {stats['inserted']}")
print(f"  Updated:  {stats['updated']}")
print(f"  Skipped:  {stats['skipped']}")
print(f"  Errors:   {stats['errors']}")

if errors:
    print("\n[WARNING] Errors encountered:")
    for error in errors[:10]:
        print(f"   - {error}")
    if len(errors) > 10:
        print(f"   ... and {len(errors) - 10} more errors")

if stats['inserted'] > 0 or stats['updated'] > 0:
    print("\n[SUCCESS] ETL completed successfully")
else:
    print("\n[WARNING] No data was inserted or updated")

print("=" * 60)
