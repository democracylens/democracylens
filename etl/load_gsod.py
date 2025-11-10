"""
ETL script to load International IDEA Global State of Democracy (GSoD) Indices into the database.
Downloads latest GSoD data from International IDEA.
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

# International IDEA GSoD data URLs
# The GSoD Indices are available on IDEA's Democracy Tracker
GSOD_URLS = [
    # Version 9 (2024 data) - official download from IDEA
    "https://www.idea.int/sites/default/files/2025-06/gsod_indices_v9.csv",
    # Fallback to previous version if v9 is not available
    "https://www.idea.int/sites/default/files/2024-11/gsod_indices_v8.csv",
]

# Minimum year to load (GSoD started in 1975 for most countries)
MIN_YEAR = 1975

# Key GSoD indices to track
# We'll focus on the main 5 attributes and key sub-indices
# The column names use _est suffix for estimate values
GSOD_INDICES = {
    # Main democracy indices (5 attributes)
    'representation_est': 'Representative Government',
    'rights_est': 'Fundamental Rights',
    'rule_law_est': 'Rule of Law',
    'participation_est': 'Participatory Engagement',

    # Sub-indices for Representative Government
    'cred_elect_est': 'Credible Elections',
    'inclu_suff_est': 'Inclusive Suffrage',
    'free_parties_est': 'Free Political Parties',
    'elected_gov_est': 'Elected Government',

    # Sub-indices for Fundamental Rights
    'access_just_est': 'Access to Justice',
    'civil_lib_est': 'Civil Liberties',
    'basic_welf_est': 'Basic Welfare',
    'pol_equal_est': 'Political Equality',
    'soc_grp_equal_est': 'Social Group Equality',
    'gender_equal_est': 'Gender Equality',

    # Rule of Law sub-indices
    'jud_ind_est': 'Judicial Independence',
    'abs_corrupt_est': 'Absence of Corruption',
    'predict_enf_est': 'Predictable Enforcement',
    'pers_integ_sec_est': 'Personal Integrity and Security',

    # Participation sub-indices
    'civil_soc_est': 'Civil Society Participation',
    'elect_part_est': 'Electoral Participation',
    'direct_dem_est': 'Direct Democracy',
    'local_dem_est': 'Local Democracy',

    # Additional important indices
    'free_express_est': 'Freedom of Expression',
    'free_press_est': 'Freedom of the Press',
    'free_assoc_assem_est': 'Freedom of Association and Assembly',
    'effect_parl_est': 'Effective Parliament',
}


def download_gsod_data():
    """Download GSoD data from International IDEA sources."""
    print("\n[INFO] Downloading International IDEA GSoD data...")

    for url in GSOD_URLS:
        try:
            print(f"[INFO] Trying URL: {url}")
            response = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})

            if response.status_code == 200:
                print(f"[SUCCESS] Downloaded {len(response.content)} bytes")
                return BytesIO(response.content), 'csv'
            else:
                print(f"[WARNING] Got status code {response.status_code}, trying next URL...")
        except Exception as e:
            print(f"[WARNING] Failed to download: {e}")
            continue

    # Fallback to local CSV if download fails
    print("[WARNING] All download attempts failed, falling back to local CSV...")
    csv_path = os.path.join(os.path.dirname(__file__), "data", "gsod_sample.csv")
    if os.path.exists(csv_path):
        return csv_path, 'csv'
    else:
        raise Exception("No data sources available (download failed and no local fallback)")


def parse_gsod_data(file_source, file_type):
    """Parse GSoD data into standardized format."""
    print("[INFO] Parsing GSoD data...")

    try:
        # Read the data
        if isinstance(file_source, str):
            # Local file path
            df = pd.read_csv(file_source)
            print(f"[SUCCESS] Loaded {len(df)} rows from local CSV")
        else:
            df = pd.read_csv(file_source)
            print(f"[SUCCESS] Loaded {len(df)} rows from CSV")

        print(f"[DEBUG] Columns found: {df.columns.tolist()[:20]}")  # Show first 20 columns
        print(f"[DEBUG] Shape: {df.shape}")

        # GSoD format typically has:
        # - country_name, country_id (ISO), year, region, subregion
        # - Then various index columns like C_A1, C_A2, etc.

        records = []

        # Identify key columns
        country_col = None
        iso_col = None
        year_col = None

        for col in df.columns:
            col_lower = col.lower()
            if 'country_name' in col_lower or col == 'country_name':
                country_col = col
            elif 'country_id' in col_lower or col == 'country_id' or 'iso' in col_lower:
                iso_col = col
            elif col_lower == 'year':
                year_col = col

        if not all([country_col, year_col]):
            print(f"[ERROR] Could not identify required columns")
            print(f"[DEBUG] country_col={country_col}, year_col={year_col}")
            raise ValueError("Unable to parse GSoD data format")

        print(f"[INFO] Using columns: country={country_col}, year={year_col}, iso={iso_col}")

        # Find which GSoD indices are present in the data
        available_indices = {code: name for code, name in GSOD_INDICES.items() if code in df.columns}
        print(f"[INFO] Found {len(available_indices)} GSoD indices in data")

        if len(available_indices) == 0:
            print("[WARNING] No recognized GSoD indices found in data")
            print(f"[DEBUG] Available columns: {df.columns.tolist()}")
            raise ValueError("No GSoD indices found in data")

        # Process each row
        for _, row in df.iterrows():
            try:
                country = row[country_col]
                year = int(row[year_col])
                iso_code = row.get(iso_col, None) if iso_col else None

                # Skip years before our floor
                if year < MIN_YEAR:
                    continue

                # Create date (GSoD data is annual, use Jan 1)
                date = f"{year}-01-01"

                # Process each available index
                for index_code, index_name in available_indices.items():
                    value = row.get(index_code, None)

                    # Skip if value is missing
                    if pd.isna(value):
                        continue

                    # GSoD scores are on 0-1 scale, convert to 0-100
                    # where 1 = highest democracy, 0 = lowest
                    scaled_value = float(value) * 100

                    records.append({
                        'country_name': str(country).strip(),
                        'iso_code': iso_code,
                        'metric_name': index_name,
                        'metric_value': round(scaled_value, 2),
                        'date': date
                    })

            except Exception as e:
                print(f"[WARNING] Error parsing row: {e}")
                continue

        result_df = pd.DataFrame(records)
        print(f"[SUCCESS] Parsed {len(result_df)} metric records")
        return result_df

    except Exception as e:
        print(f"[ERROR] Failed to parse data: {e}")
        raise


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
        'United Kingdom of Great Britain and Northern Ireland': 'United Kingdom',
        'United Kingdom': 'United Kingdom',
        'UK': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        'South Korea': 'South Korea',
        'Korea, South': 'South Korea',
        'Korea (South)': 'South Korea',
        'Republic of Korea': 'South Korea',
        'Korea, Republic of': 'South Korea',
    }

    if name in variations and variations[name] in country_cache:
        return country_cache[variations[name]]

    return None


# Main execution
print("=" * 60)
print("International IDEA GSoD ETL - Democracy Indices Loader")
print("=" * 60)
print(f"Minimum year: {MIN_YEAR}")

# Download data
try:
    file_source, file_type = download_gsod_data()
except Exception as e:
    print(f"\n[ERROR] Failed to download data: {e}")
    print("[INFO] Exiting...")
    exit(1)

# Parse data
try:
    df = parse_gsod_data(file_source, file_type)
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
                        'source': 'International IDEA'
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
                            'source': 'International IDEA',
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
