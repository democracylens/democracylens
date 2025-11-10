"""
ETL script to load V-Dem (Varieties of Democracy) indicators into the database.
Downloads the latest V-Dem dataset from their GitHub releases.

V-Dem provides comprehensive democracy indicators for 200+ countries from 1789-present.
We'll focus on the core democracy indices:
- Electoral Democracy Index (v2x_polyarchy)
- Liberal Democracy Index (v2x_libdem)
- Participatory Democracy Index (v2x_partipdem)
- Deliberative Democracy Index (v2x_delibdem)
- Egalitarian Democracy Index (v2x_egaldem)

Data source: https://www.v-dem.net/
GitHub: https://github.com/vdeminstitute/vdemdata
"""

import os
import requests
import pandas as pd
from io import BytesIO
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

# V-Dem indicator columns to load
# Format: (column_name, friendly_name, description)
VDEM_INDICATORS = [
    ('v2x_polyarchy', 'Electoral Democracy Index', 'Electoral principle of democracy (0-1 scale)'),
    ('v2x_libdem', 'Liberal Democracy Index', 'Liberal principle of democracy (0-1 scale)'),
    ('v2x_partipdem', 'Participatory Democracy Index', 'Participatory principle (0-1 scale)'),
    ('v2x_delibdem', 'Deliberative Democracy Index', 'Deliberative principle (0-1 scale)'),
    ('v2x_egaldem', 'Egalitarian Democracy Index', 'Egalitarian principle (0-1 scale)'),
]

# Minimum year (user-specified floor)
MIN_YEAR = 1960

# V-Dem dataset URLs to try
VDEM_URLS = [
    # Try latest release from GitHub
    "https://github.com/vdeminstitute/vdemdata/raw/master/inst/extdata/vdem.csv",
    # Alternative: Try v-dem.net direct download
    "https://v-dem.net/static/website/img/refs/vdemds/country_year.csv",
]


def download_vdem_data():
    """Download V-Dem dataset from their repository."""
    print("\n[INFO] Downloading V-Dem dataset...")
    print("[WARNING] V-Dem dataset is large (~100MB), this may take a minute...")

    for url in VDEM_URLS:
        try:
            print(f"[INFO] Trying URL: {url}")
            response = requests.get(url, timeout=120)  # Longer timeout for large file

            if response.status_code == 200:
                print(f"[SUCCESS] Downloaded {len(response.content)} bytes")
                return BytesIO(response.content)
            else:
                print(f"[WARNING] Got status code {response.status_code}, trying next URL...")
        except Exception as e:
            print(f"[WARNING] Failed to download: {e}")
            continue

    print("[ERROR] All download attempts failed")
    return None


def parse_vdem_data(data_source):
    """Parse V-Dem CSV data into our standard format."""
    print("[INFO] Parsing V-Dem data...")

    try:
        # V-Dem CSV has columns: country_name, country_text_id, year, [indicators...]
        df = pd.read_csv(data_source, low_memory=False)
        print(f"[INFO] Loaded {len(df)} rows from V-Dem dataset")

        # Check for required columns
        required_cols = ['country_name', 'year']
        indicator_cols = [ind[0] for ind in VDEM_INDICATORS]

        # Find which indicator columns exist
        available_indicators = [
            (col, name, desc) for col, name, desc in VDEM_INDICATORS
            if col in df.columns
        ]

        if not available_indicators:
            print(f"[ERROR] No indicator columns found. Available columns: {df.columns.tolist()[:20]}")
            return None

        print(f"[INFO] Found {len(available_indicators)} of {len(VDEM_INDICATORS)} indicators")

        # Filter by year
        df = df[df['year'] >= MIN_YEAR].copy()
        print(f"[INFO] Filtered to {len(df)} rows from {MIN_YEAR} onwards")

        # Transform to long format
        records = []
        for _, row in df.iterrows():
            country = row['country_name']
            year = row['year']

            # Skip if year is invalid
            if pd.isna(year) or not (1000 < year < 3000):
                continue

            date = f"{int(year)}-01-01"

            # Extract each indicator
            for col, name, desc in available_indicators:
                value = row.get(col)

                # Skip missing values
                if pd.isna(value):
                    continue

                # V-Dem indices are on 0-1 scale, convert to 0-100 for consistency
                try:
                    value_float = float(value)
                    value_100 = value_float * 100
                except (ValueError, TypeError):
                    continue

                records.append({
                    'country_name': country,
                    'metric_name': name,
                    'metric_value': round(value_100, 2),
                    'date': date
                })

        df_transformed = pd.DataFrame(records)
        print(f"[SUCCESS] Transformed to {len(df_transformed)} metric records")
        return df_transformed

    except Exception as e:
        print(f"[ERROR] Failed to parse V-Dem data: {e}")
        return None


def normalize_country_name(name, country_cache):
    """Match country name to database."""
    # Direct match
    if name in country_cache:
        return country_cache[name]

    # Common V-Dem variations
    variations = {
        'United States of America': 'United States',
        'United Kingdom of Great Britain and Northern Ireland': 'United Kingdom',
        'Republic of Korea': 'South Korea',
        'Korea, Republic of': 'South Korea',
    }

    if name in variations and variations[name] in country_cache:
        return country_cache[variations[name]]

    return None


# Main execution
print("=" * 60)
print("V-Dem ETL - Democracy Indices Loader")
print("=" * 60)
print(f"Minimum year: {MIN_YEAR}")
print(f"Indicators: {len(VDEM_INDICATORS)}")

# Download data
data_source = download_vdem_data()
if data_source is None:
    print("[ERROR] Failed to download V-Dem data. Exiting.")
    exit(1)

# Parse data
df = parse_vdem_data(data_source)
if df is None or len(df) == 0:
    print("[ERROR] Failed to parse V-Dem data or no data available. Exiting.")
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
        print(f"   Processing {len(df)} records...")

        # Process each record
        for idx, record in df.iterrows():
            try:
                # Match country
                country_id = normalize_country_name(record['country_name'], country_cache)

                if not country_id:
                    if stats['skipped'] < 5:
                        errors.append(f"Country '{record['country_name']}' not in database")
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
                        'source': 'V-Dem'
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
                            'source': 'V-Dem',
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
