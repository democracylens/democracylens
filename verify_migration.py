"""Quick script to verify events table exists."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://{os.environ['DB_ADMIN_USER']}:{os.environ['DB_ADMIN_PW']}@"
    f"{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
    f"?sslmode=require",
    pool_pre_ping=True,
)

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM events"))
    count = result.scalar()
    print(f"[OK] Events table exists with {count} events")

    # Check indexes
    result = conn.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'events'
    """))
    indexes = [row[0] for row in result]
    print(f"[OK] Found {len(indexes)} indexes: {', '.join(indexes)}")

print("\n[SUCCESS] Migration successful!")
