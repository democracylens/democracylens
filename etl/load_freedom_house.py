"""
ETL script to load Freedom House democracy metrics into the database.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(override=True)

# Database connection (with SSL for Supabase)
engine = create_engine(
    f"postgresql+psycopg2://{os.environ['DB_ADMIN_USER']}:{os.environ['DB_ADMIN_PW']}@"
    f"{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
    f"?sslmode=require",
    pool_pre_ping=True,
)

# Load CSV data
csv_path = os.path.join(os.path.dirname(__file__), "data", "freedom_house_sample.csv")
print(f"📂 Loading data from {csv_path}...")

try:
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} rows from CSV")
except FileNotFoundError:
    print(f"❌ ERROR: File not found: {csv_path}")
    exit(1)
except Exception as e:
    print(f"❌ ERROR reading CSV: {e}")
    exit(1)

# Validate required columns
required_columns = {'country_name', 'metric_name', 'metric_value', 'date'}
missing_columns = required_columns - set(df.columns)
if missing_columns:
    print(f"❌ ERROR: Missing required columns: {missing_columns}")
    exit(1)

print("\n🔄 Processing data...")

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

        # Process each row
        for idx, row in df.iterrows():
            try:
                country_name = row['country_name']

                # Lookup country_id
                country_id = country_cache.get(country_name)
                if not country_id:
                    errors.append(f"Row {idx+2}: Country '{country_name}' not found in database")
                    stats['skipped'] += 1
                    continue

                # Insert or update metric (upsert on conflict)
                # Note: Since we don't have a unique constraint, we'll check for duplicates manually
                check_result = conn.execute(
                    text("""
                        SELECT id FROM metrics
                        WHERE country_id = :country_id
                        AND metric_name = :metric_name
                        AND date = :date
                    """),
                    {
                        'country_id': country_id,
                        'metric_name': row['metric_name'],
                        'date': row['date']
                    }
                )
                existing = check_result.fetchone()

                if existing:
                    # Update existing record
                    conn.execute(
                        text("""
                            UPDATE metrics
                            SET metric_value = :metric_value, source = :source
                            WHERE id = :id
                        """),
                        {
                            'id': existing.id,
                            'metric_value': float(row['metric_value']),
                            'source': "Freedom House"
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
                            'source': "Freedom House",
                            'date': row['date']
                        }
                    )
                    stats['inserted'] += 1

            except Exception as e:
                errors.append(f"Row {idx+2}: {str(e)}")
                stats['errors'] += 1

        # Commit happens automatically at end of 'with' block
        print("✅ Transaction committed")

except Exception as e:
    print(f"\n❌ Database error: {e}")
    exit(1)

# Print summary
print("\n" + "=" * 60)
print("📊 ETL Summary")
print("=" * 60)
print(f"  Inserted: {stats['inserted']}")
print(f"  Updated:  {stats['updated']}")
print(f"  Skipped:  {stats['skipped']}")
print(f"  Errors:   {stats['errors']}")

if errors:
    print("\n⚠️  Errors encountered:")
    for error in errors[:10]:  # Show first 10 errors
        print(f"   • {error}")
    if len(errors) > 10:
        print(f"   ... and {len(errors) - 10} more errors")

if stats['inserted'] > 0 or stats['updated'] > 0:
    print("\n✅ ETL completed successfully")
else:
    print("\n⚠️  No data was inserted or updated")

print("=" * 60)
