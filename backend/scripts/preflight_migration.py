"""Run before alembic upgrade head. Exits with code 1 and clear instructions if guard fails."""
import os
import sys
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
if not url:
    print("ABORT: DATABASE_URL not set")
    sys.exit(1)
engine = create_engine(url)
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS _migration_check (id INT)"))
        conn.execute(text("DROP TABLE IF EXISTS _migration_check"))
        conn.commit()
except Exception as e:
    print(f"ABORT: Database not writable: {e}")
    print("DATABASE_URL may point to read replica — use primary DB")
    sys.exit(1)

# Check sessions row count for large-table guard
with engine.connect() as conn:
    # sessions table may not exist pre-migration
    try:
        r = conn.execute(text("SELECT COUNT(*) FROM sessions"))
        count = r.scalar() if hasattr(r, "scalar") else r.fetchone()[0]
        if count > 1000:
            print("ABORT: sessions table has >1000 rows. Run manual UPDATE first:")
            print(
                '  psql $DATABASE_URL -c "UPDATE sessions SET process_type = \'mig\' WHERE process_type IS NULL"'
            )
            print(
                '  psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions WHERE process_type IS NULL"  # must be 0'
            )
            sys.exit(1)
    except Exception:
        pass  # sessions table may not exist yet

print("Pre-flight OK")
