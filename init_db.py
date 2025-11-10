"""
Database initialization script for Democracy Lens.
Applies schema and seeds initial country data.

Compatible with PostgreSQL 12+ (tested with Neon).
Requires admin credentials configured in .env file.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_ADMIN_USER = os.getenv("DB_ADMIN_USER")
DB_ADMIN_PW = os.getenv("DB_ADMIN_PW")

# Initial country seed data (top democracies and diverse regions)
SEED_COUNTRIES = [
    ("United States", "USA"),
    ("United Kingdom", "GBR"),
    ("Germany", "DEU"),
    ("France", "FRA"),
    ("Japan", "JPN"),
    ("Canada", "CAN"),
    ("Australia", "AUS"),
    ("India", "IND"),
    ("Brazil", "BRA"),
    ("South Africa", "ZAF"),
    ("Mexico", "MEX"),
    ("Argentina", "ARG"),
    ("South Korea", "KOR"),
    ("Poland", "POL"),
    ("Spain", "ESP"),
]


def main():
    """Initialize the database with schema and seed data."""

    print("=" * 60)
    print("Democracy Lens Database Initialization")
    print("=" * 60)

    # Validate environment variables
    if not all([DB_HOST, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PW]):
        print("[ERROR] Missing required environment variables")
        print("   Required: DB_HOST, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PW")
        return False

    try:
        # Connect to database
        print(f"\n[INFO] Connecting to database at {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_ADMIN_USER,
            password=DB_ADMIN_PW
        )
        cursor = conn.cursor()
        print("[SUCCESS] Connected successfully")

        # Apply schema
        print("\n[INFO] Applying database schema...")
        with open("schema.sql", "r") as f:
            schema_sql = f.read()

        cursor.execute(schema_sql)
        conn.commit()
        print("[SUCCESS] Schema applied successfully")

        # Seed countries table
        print("\n[INFO] Seeding countries table...")

        # Check if countries already exist
        cursor.execute("SELECT COUNT(*) FROM countries")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"[WARNING] Found {existing_count} existing countries")
            response = input("   Overwrite existing data? (y/N): ").strip().lower()
            if response != 'y':
                print("   Skipping country seed")
            else:
                cursor.execute("TRUNCATE TABLE metrics CASCADE")
                cursor.execute("TRUNCATE TABLE countries RESTART IDENTITY CASCADE")
                conn.commit()
                existing_count = 0

        if existing_count == 0:
            for name, iso_code in SEED_COUNTRIES:
                cursor.execute(
                    "INSERT INTO countries (name, iso_code) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (name, iso_code)
                )
            conn.commit()
            print(f"[SUCCESS] Seeded {len(SEED_COUNTRIES)} countries")

        # Verify setup
        print("\n[INFO] Verifying database setup...")

        cursor.execute("SELECT COUNT(*) FROM countries")
        country_count = cursor.fetchone()[0]
        print(f"   Countries: {country_count}")

        cursor.execute("SELECT COUNT(*) FROM metrics")
        metric_count = cursor.fetchone()[0]
        print(f"   Metrics: {metric_count}")

        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'metrics'
            AND indexname = 'metrics_country_metric_date_idx'
        """)
        index_exists = cursor.fetchone() is not None
        print(f"   Index: {'[OK] Present' if index_exists else '[MISSING] Missing'}")

        # Close connection
        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("[SUCCESS] Database initialization complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Create read-only user in Neon SQL Editor (see DEPLOYMENT.md)")
        print("  2. Run ETL script: python etl/load_freedom_house.py")
        print("  3. Start app: streamlit run app.py")

        return True

    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        return False
    except FileNotFoundError:
        print("\n[ERROR] schema.sql not found")
        print("   Make sure you're running this from the project root")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
