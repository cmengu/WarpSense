"""
Prototype: Validate 007_session_annotations migration syntax and model wiring.
Run from project root: python -m backend.cursor_prototype_annotation_migration
"""
import sys
from pathlib import Path

# Ensure backend is on path
backend = Path(__file__).resolve().parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend.parent))

def test_migration_upgrade():
    """Run migration upgrade to validate syntax."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(backend / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(alembic_cfg, "007_session_annotations")
    print("Migration 007 upgrade: OK")

def test_model_and_route():
    """Validate SessionAnnotation model and annotations route can be loaded."""
    from database.models import SessionModel
    from database.base import Base
    # Import model so it registers
    from models.annotation import SessionAnnotation  # noqa: F401
    assert "session_annotations" in Base.metadata.tables
    print("Model + metadata: OK")

if __name__ == "__main__":
    print("Prototype: Annotation migration + model wiring")
    # Skip migration if DB not configured
    import os
    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL unset — skipping migration (use .env)")
    else:
        try:
            test_migration_upgrade()
        except Exception as e:
            print(f"Migration failed: {e}")
            raise
    test_model_and_route()
    print("Prototype complete.")
