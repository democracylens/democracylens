"""
ETL script to load Freedom House democracy metrics into the database.
Downloads latest data from Freedom House website.
"""

import os
import re
import pandas as pd
import requests
from io import BytesIO
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime

load_dotenv(override=True)

# Database connection with SSL
engine = create_engine(
    f"postgresql+psycopg2://{os.environ['DB_ADMIN_USER']}:{os.environ['DB_ADMIN_PW']}@"
    f"{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
    f"?sslmode=require",
    pool_pre_ping=True,
)

# Freedom House data URLs (updated annually)
# We'll try to fetch the most comprehensive historical dataset
FREEDOM_HOUSE_URLS = [
    # Try the all-data comprehensive file first (most complete)
    "https://freedomhouse.org/sites/default/files/2024-02/All_data_FIW_2013-2024.xlsx",
    "https://freedomhouse.org/sites/default/files/2023-02/All_data_FIW_2013-2023.xlsx",
    # Fallback to aggregate scores file
    "https://freedomhouse.org/sites/default/files/2024-02/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx",
    "https://freedomhouse.org/sites/default/files/2023-02/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2023.xlsx",
]

# Minimum year to load (user-specified floor)
MIN_YEAR = 1960

def download_freedom_house_data():
    """Download Freedom House data from their website."""
    print("\n[INFO] Downloading Freedom House data...")

    for url in FREEDOM_HOUSE_URLS:
        try:
            print(f"[INFO] Trying URL: {url}")
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                print(f"[SUCCESS] Downloaded {len(response.content)} bytes")
                return BytesIO(response.content), url
            else:
                print(f"[WARNING] Got status code {response.status_code}, trying next URL...")
        except Exception as e:
            print(f"[WARNING] Failed to download: {e}")
            continue

    # Fallback to local CSV if download fails
    print("[WARNING] All download attempts failed, falling back to local CSV...")
    csv_path = os.path.join(os.path.dirname(__file__), "data", "freedom_house_sample.csv")
    return csv_path, None


def parse_freedom_house_excel(file_source, source_url):
    """Parse Freedom House Excel file into standardized format."""
    print("[INFO] Parsing Freedom House data...")

    try:
        # If it's a file path (string), read directly
        if isinstance(file_source, str):
            df = pd.read_csv(file_source)
            print(f"[SUCCESS] Loaded {len(df)} rows from local CSV")
            return df

        # Otherwise, it's downloaded Excel data
        excel_file = pd.ExcelFile(file_source)
        print(f"[INFO] Excel file contains sheets: {excel_file.sheet_names}")

        # Try to find the main data sheet
        # Freedom House uses different sheet names
        data_sheet = None
        for sheet_name in excel_file.sheet_names:
            if any(keyword in sheet_name.lower() for keyword in ['country', 'data', 'ratings', 'fh']):
                data_sheet = sheet_name
                break

        if not data_sheet:
            data_sheet = excel_file.sheet_names[0]  # Use first sheet as fallback

        print(f"[INFO] Using sheet: {data_sheet}")
        df = pd.read_excel(file_source, sheet_name=data_sheet)

        # Parse based on file type
        if 'All_data' in source_url:
            # Comprehensive file with detailed metrics
            df = parse_all_data_format(df)
        else:
            # Aggregate ratings file
            df = parse_ratings_format(df)

        print(f"[SUCCESS] Parsed {len(df)} rows")
        return df

    except Exception as e:
        print(f"[ERROR] Failed to parse data: {e}")
        raise


def parse_all_data_format(df):
    """Parse the comprehensive All_data file format."""
    print("[INFO] Parsing comprehensive format...")

    # The All_data format has columns: Country/Territory, Edition, Status, PR, CL, Total
    # We need to transform this into our standard format

    records = []

    for _, row in df.iterrows():
        try:
            country = row.get('Country/Territory', row.get('Country', ''))
            year_str = str(row.get('Edition', ''))

            # Extract year from edition (e.g., "2024" or "2024 edition")
            year_match = re.search(r'(\d{4})', year_str)
            if not year_match:
                continue

            year = int(year_match.group(1))

            # Skip years before our floor
            if year < MIN_YEAR:
                continue

            # Create date (Freedom House data is annual, use Jan 1)
            date = f"{year}-01-01"

            # Extract metrics
            pr = row.get('PR', None)  # Political Rights
            cl = row.get('CL', None)  # Civil Liberties

            if pd.notna(pr):
                # Freedom House uses 1-7 scale, convert to 0-100 (reverse scale)
                # 1 = most free (100), 7 = least free (0)
                pr_score = ((7 - float(pr)) / 6) * 100
                records.append({
                    'country_name': country,
                    'metric_name': 'Political Rights',
                    'metric_value': round(pr_score, 2),
                    'date': date
                })

            if pd.notna(cl):
                cl_score = ((7 - float(cl)) / 6) * 100
                records.append({
                    'country_name': country,
                    'metric_name': 'Civil Liberties',
                    'metric_value': round(cl_score, 2),
                    'date': date
                })

            # Calculate Freedom Score (average of PR and CL)
            if pd.notna(pr) and pd.notna(cl):
                freedom_score = (pr_score + cl_score) / 2
                records.append({
                    'country_name': country,
                    'metric_name': 'Freedom Score',
                    'metric_value': round(freedom_score, 2),
                    'date': date
                })

        except Exception as e:
            print(f"[WARNING] Error parsing row: {e}")
            continue

    return pd.DataFrame(records)


def parse_ratings_format(df):
    """Parse the aggregate ratings file format."""
    print("[INFO] Parsing ratings format...")

    # This format has country in first column, then year columns
    # Need to melt the dataframe

    records = []

    # Identify country column (usually first column or named 'Country')
    country_col = df.columns[0]

    # Get year columns (columns that look like years: 1972, 1973, etc.)
    year_cols = [col for col in df.columns if str(col).isdigit() and 1900 < int(str(col)) < 2100]

    for _, row in df.iterrows():
        country = row[country_col]

        for year_col in year_cols:
            year = int(str(year_col))

            # Skip years before our floor
            if year < MIN_YEAR:
                continue

            value = row[year_col]

            if pd.notna(value):
                # These files typically have status or ratings
                # We'll store as-is and document the scale
                records.append({
                    'country_name': country,
                    'metric_name': 'Freedom Status',
                    'metric_value': value if isinstance(value, (int, float)) else 0,
                    'date': f"{year}-01-01"
                })

    return pd.DataFrame(records)


def normalize_country_name(name, country_cache):
    """Try to match country name to database, handling variations."""
    # Direct match
    if name in country_cache:
        return country_cache[name]

    # Try ISO code match
    if len(name) == 3 and name.upper() in country_cache:
        return country_cache[name.upper()]

    # Common variations
    variations = {
        'United States': 'United States',
        'USA': 'United States',
        'United Kingdom': 'United Kingdom',
        'UK': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        'South Korea': 'South Korea',
        'Korea, South': 'South Korea',
    }

    if name in variations and variations[name] in country_cache:
        return country_cache[variations[name]]

    return None


# Main execution
print("=" * 60)
print("Freedom House ETL - Democracy Metrics Loader")
print("=" * 60)
print(f"Minimum year: {MIN_YEAR}")

# Download data
file_source, source_url = download_freedom_house_data()

# Parse data
try:
    df = parse_freedom_house_excel(file_source, source_url)
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

                # Lookup country_id with normalization
                country_id = normalize_country_name(country_name, country_cache)
                if not country_id:
                    if stats['skipped'] < 5:  # Only show first 5 skipped countries
                        errors.append(f"Country '{country_name}' not found in database")
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
                        'source': 'Freedom House'
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
                            'source': 'Freedom House',
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
