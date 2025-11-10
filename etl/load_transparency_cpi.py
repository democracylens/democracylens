"""
ETL script to load Transparency International Corruption Perceptions Index into the database.
Downloads latest CPI data from Transparency International or DataHub.io.
"""

import os
import re
import pandas as pd
import requests
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

# Transparency International CPI data URLs
# DataHub.io provides clean CSV format, Transparency.org has Excel files
TI_CPI_URLS = [
    # DataHub.io CSV (clean, standardized format)
    "https://pkgstore.datahub.io/core/corruption-perceptions-index/cpi_0/data/dc96ec931033177e6133be8bbe26e2c4/cpi_0.csv",
    # GitHub backup (datasets organization maintains this)
    "https://raw.githubusercontent.com/datasets/corruption-perceptions-index/main/data/cpi.csv",
    # Transparency.org official (may need to be updated annually)
    "https://www.transparency.org/en/cpi/2024/table/cpi",
]

# Minimum year to load (CPI started in 1995)
MIN_YEAR = 1995


def download_cpi_data():
    """Download CPI data from available sources."""
    print("\n[INFO] Downloading Transparency International CPI data...")

    for url in TI_CPI_URLS:
        try:
            print(f"[INFO] Trying URL: {url}")
            response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})

            if response.status_code == 200:
                print(f"[SUCCESS] Downloaded {len(response.content)} bytes")
                # Determine if it's CSV or Excel based on URL
                if url.endswith('.csv') or 'csv' in url.lower():
                    return BytesIO(response.content), 'csv'
                else:
                    return BytesIO(response.content), 'excel'
            else:
                print(f"[WARNING] Got status code {response.status_code}, trying next URL...")
        except Exception as e:
            print(f"[WARNING] Failed to download: {e}")
            continue

    # Fallback to local CSV if download fails
    print("[WARNING] All download attempts failed, falling back to local CSV...")
    csv_path = os.path.join(os.path.dirname(__file__), "data", "cpi_sample.csv")
    if os.path.exists(csv_path):
        return csv_path, 'csv'
    else:
        raise Exception("No data sources available (download failed and no local fallback)")


def parse_cpi_data(file_source, file_type):
    """Parse CPI data into standardized format."""
    print("[INFO] Parsing CPI data...")

    try:
        # Read the data
        if isinstance(file_source, str):
            # Local file path
            df = pd.read_csv(file_source)
            print(f"[SUCCESS] Loaded {len(df)} rows from local CSV")
        elif file_type == 'csv':
            df = pd.read_csv(file_source)
            print(f"[SUCCESS] Loaded {len(df)} rows from CSV")
        else:
            # Excel format
            df = pd.read_excel(file_source)
            print(f"[SUCCESS] Loaded {len(df)} rows from Excel")

        print(f"[DEBUG] Columns found: {df.columns.tolist()}")
        print(f"[DEBUG] First few rows:\n{df.head()}")

        # DataHub.io format has columns: Jurisdiction, ISO3, Year, CPI score 2024, Rank, Sources, Standard Error
        # We need: Country, Year, CPI Score

        records = []

        # Identify column names (handle variations)
        country_col = None
        year_col = None
        score_col = None
        iso_col = None

        for col in df.columns:
            col_lower = col.lower()
            if 'jurisdiction' in col_lower or 'country' in col_lower or 'territory' in col_lower:
                country_col = col
            elif 'year' in col_lower:
                year_col = col
            elif 'cpi' in col_lower and 'score' in col_lower:
                score_col = col
            elif 'iso' in col_lower and ('3' in col_lower or 'code' in col_lower):
                iso_col = col

        # If we have year columns instead of a year column, need to melt
        if year_col is None:
            # Check if columns are years (1995, 1996, etc.)
            year_cols = [col for col in df.columns
                        if str(col).isdigit() and 1900 < int(str(col)) < 2100]

            if year_cols:
                print(f"[INFO] Found year columns: {year_cols[:5]}... (showing first 5)")
                # Wide format - need to melt
                return parse_wide_format(df, country_col, iso_col, year_cols)

        # Long format
        if not all([country_col, year_col, score_col]):
            print(f"[ERROR] Could not identify required columns")
            print(f"[DEBUG] country_col={country_col}, year_col={year_col}, score_col={score_col}")
            raise ValueError("Unable to parse CPI data format")

        print(f"[INFO] Using columns: country={country_col}, year={year_col}, score={score_col}")

        for _, row in df.iterrows():
            try:
                country = row[country_col]
                year = int(row[year_col])
                score = row[score_col]

                # Skip years before our floor
                if year < MIN_YEAR:
                    continue

                # Skip if score is missing
                if pd.isna(score):
                    continue

                # Create date (CPI data is annual, use Jan 1)
                date = f"{year}-01-01"

                # CPI score is already on 0-100 scale (where 100 = very clean, 0 = highly corrupt)
                records.append({
                    'country_name': str(country).strip(),
                    'iso_code': row.get(iso_col, None) if iso_col else None,
                    'metric_name': 'Corruption Perceptions Index',
                    'metric_value': round(float(score), 2),
                    'date': date
                })

            except Exception as e:
                print(f"[WARNING] Error parsing row: {e}")
                continue

        result_df = pd.DataFrame(records)
        print(f"[SUCCESS] Parsed {len(result_df)} rows")
        return result_df

    except Exception as e:
        print(f"[ERROR] Failed to parse data: {e}")
        raise


def parse_wide_format(df, country_col, iso_col, year_cols):
    """Parse wide format where years are columns."""
    print("[INFO] Parsing wide format...")

    records = []

    for _, row in df.iterrows():
        country = row[country_col]
        iso_code = row.get(iso_col, None) if iso_col else None

        for year_col in year_cols:
            year = int(str(year_col))

            # Skip years before our floor
            if year < MIN_YEAR:
                continue

            score = row[year_col]

            # Skip if score is missing or invalid
            if pd.isna(score):
                continue

            # Handle string values like '-' or empty strings
            if isinstance(score, str):
                score = score.strip()
                if score == '-' or score == '' or score == 'N/A':
                    continue
                try:
                    score = float(score)
                except ValueError:
                    continue

            # Create date
            date = f"{year}-01-01"

            records.append({
                'country_name': str(country).strip(),
                'iso_code': iso_code,
                'metric_name': 'Corruption Perceptions Index',
                'metric_value': round(float(score), 2),
                'date': date
            })

    return pd.DataFrame(records)


def normalize_country_name(name, iso_code, country_cache):
    """Try to match country name to database, handling variations."""
    # Try ISO code first (most reliable)
    if iso_code and iso_code in country_cache:
        return country_cache[iso_code]

    # Direct name match
    if name in country_cache:
        return country_cache[name]

    # Try ISO code as string match
    if len(name) == 3 and name.upper() in country_cache:
        return country_cache[name.upper()]

    # Common variations
    variations = {
        'United States of America': 'United States',
        'USA': 'United States',
        'United Kingdom': 'United Kingdom',
        'UK': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        'South Korea': 'South Korea',
        'Korea, South': 'South Korea',
        'Korea (South)': 'South Korea',
        'Republic of Korea': 'South Korea',
    }

    if name in variations and variations[name] in country_cache:
        return country_cache[variations[name]]

    return None


# Main execution
print("=" * 60)
print("Transparency International CPI ETL - Corruption Data Loader")
print("=" * 60)
print(f"Minimum year: {MIN_YEAR}")

# Download data
try:
    file_source, file_type = download_cpi_data()
except Exception as e:
    print(f"\n[ERROR] Failed to download data: {e}")
    print("[INFO] Exiting...")
    exit(1)

# Parse data
try:
    df = parse_cpi_data(file_source, file_type)
except Exception as e:
    print(f"\n[ERROR] Failed to parse data: {e}")
    print("[INFO] Exiting...")
    exit(1)

# Validate required columns
required_columns = {'country_name', 'metric_name', 'metric_value', 'date'}
missing_columns = required_columns - set(df.columns)
if missing_columns:
    print(f"[ERROR] Missing required columns: {missing_columns}")
    exit(1)

print("\n[INFO] Processing data...")

# Track statistics
stats = defaultdict(int)
errors = []

try:
    with engine.begin() as conn:
        # Build a cache of country_id lookups
        country_cache = {}
        result = conn.execute(text("SELECT id, name, iso_code FROM countries"))
        for row in result:
            country_cache[row.name] = row.id
            if hasattr(row, 'iso_code') and row.iso_code:
                country_cache[row.iso_code] = row.id

        print(f"   Found {len(country_cache)} countries in database")
        print(f"   Processing {len(df)} metric records...")

        # Process each row
        for idx, row in df.iterrows():
            try:
                country_name = row['country_name']
                iso_code = row.get('iso_code', None)

                # Lookup country_id with normalization
                country_id = normalize_country_name(country_name, iso_code, country_cache)
                if not country_id:
                    if stats['skipped'] < 5:  # Only show first 5 skipped countries
                        errors.append(f"Country '{country_name}' (ISO: {iso_code}) not found in database")
                    stats['skipped'] += 1
                    continue

                # Insert or update metric (upsert)
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
                        'metric_name': row['metric_name'],
                        'date': row['date'],
                        'source': 'Transparency International'
                    }
                )
                existing = check_result.fetchone()

                if existing:
                    # Update existing record
                    conn.execute(
                        text("""
                            UPDATE metrics
                            SET metric_value = :metric_value
                            WHERE id = :id
                        """),
                        {
                            'id': existing.id,
                            'metric_value': float(row['metric_value'])
                        }
                    )
                    stats['updated'] += 1
                else:
                    # Insert new record
                    conn.execute(
                        text("""
                            INSERT INTO metrics (country_id, metric_name, metric_value, source, date)
                            VALUES (:country_id, :metric_name, :metric_value, :source, :date)
                        """),
                        {
                            'country_id': country_id,
                            'metric_name': row['metric_name'],
                            'metric_value': float(row['metric_value']),
                            'source': 'Transparency International',
                            'date': row['date']
                        }
                    )
                    stats['inserted'] += 1

            except Exception as e:
                errors.append(f"Row {idx+2}: {str(e)}")
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
    for error in errors[:10]:  # Show first 10 errors
        print(f"   - {error}")
    if len(errors) > 10:
        print(f"   ... and {len(errors) - 10} more errors")

if stats['inserted'] > 0 or stats['updated'] > 0:
    print("\n[SUCCESS] ETL completed successfully")
else:
    print("\n[WARNING] No data was inserted or updated")

print("=" * 60)
