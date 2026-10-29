from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.app.core.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def run_auto_migrations(engine_instance=engine):
    """
    Applies non-destructive schema migrations for existing SQLite databases.
    Ensures newly added columns exist without resetting the database.
    """
    from sqlalchemy import text
    with engine_instance.connect() as conn:
        def add_column_if_missing(table: str, col_name: str, col_type: str):
            try:
                res = conn.execute(text(f"PRAGMA table_info({table});")).fetchall()
                existing_cols = [r[1] for r in res]
                if existing_cols and col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
            except Exception:
                pass

        # flags
        add_column_if_missing("flags", "actionability", "VARCHAR(50) DEFAULT 'INTERNAL_REVIEW_ONLY'")
        # documents
        add_column_if_missing("documents", "official_verification_status", "VARCHAR(50) DEFAULT 'pending_review'")
        add_column_if_missing("documents", "official_verification_remarks", "VARCHAR(500)")
        add_column_if_missing("documents", "official_verified_by", "INTEGER")
        add_column_if_missing("documents", "official_verified_at", "DATETIME")
        # verification_results
        add_column_if_missing("verification_results", "verification_mode", "VARCHAR(30) DEFAULT 'SIMULATED'")
        add_column_if_missing("verification_results", "manual_remarks", "VARCHAR(500)")
        add_column_if_missing("verification_results", "manual_verified_by", "INTEGER")
        add_column_if_missing("verification_results", "manual_reference_no", "VARCHAR(100)")
        add_column_if_missing("verification_results", "ocr_reference_no", "VARCHAR(100)")
        # information_requests
        add_column_if_missing("information_requests", "reason", "TEXT DEFAULT ''")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
