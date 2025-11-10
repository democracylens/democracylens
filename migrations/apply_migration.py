"""
Apply database migrations to Democracy Lens database.
"""

import os
import sys
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


def apply_migration(migration_file):
    """Apply a single migration file."""

    print(f"\n[INFO] Applying migration: {migration_file}")

    # Validate environment variables
    if not all([DB_HOST, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PW]):
        print("[ERROR] Missing required environment variables")
        print("   Required: DB_HOST, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PW")
        return False

    try:
        # Connect to database
        print(f"[INFO] Connecting to database at {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_ADMIN_USER,
            password=DB_ADMIN_PW
        )
        cursor = conn.cursor()
        print("[SUCCESS] Connected successfully")

        # Read and execute migration
        migration_path = os.path.join(os.path.dirname(__file__), migration_file)

        if not os.path.exists(migration_path):
            print(f"[ERROR] Migration file not found: {migration_path}")
            return False

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        print(f"[INFO] Executing migration SQL...")
        cursor.execute(migration_sql)
        conn.commit()
        print("[SUCCESS] Migration applied successfully")

        # Close connection
        cursor.close()
        conn.close()

        return True

    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <migration_file>")
        print("\nAvailable migrations:")
        migrations_dir = os.path.dirname(__file__)
        for f in sorted(os.listdir(migrations_dir)):
            if f.endswith('.sql'):
                print(f"  - {f}")
        sys.exit(1)

    migration_file = sys.argv[1]
    success = apply_migration(migration_file)
    sys.exit(0 if success else 1)
