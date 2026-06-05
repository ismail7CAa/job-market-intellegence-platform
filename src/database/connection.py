"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database manager for SQLAlchemy connections."""
    
    def __init__(self, database_url: str):
        """Initialize database connection.
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        
        # Handle SQLite for testing
        if database_url.startswith("sqlite"):
            engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
        else:
            engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        
        self.engine = engine
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        
        logger.info(f"Database initialized: {database_url}")
    
    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all database tables."""
        from .models import Base
        Base.metadata.create_all(bind=self.engine)
        self._ensure_sqlite_job_posting_columns()
        logger.info("Database tables created")

    def _ensure_sqlite_job_posting_columns(self):
        """Add repository-era columns to existing local SQLite databases."""
        if not self.database_url.startswith("sqlite"):
            return

        expected_columns = {
            "country": "VARCHAR(100) DEFAULT 'Germany'",
            "city": "VARCHAR(120)",
            "federal_state": "VARCHAR(120)",
            "salary_period": "VARCHAR(50)",
            "salary_is_estimated": "BOOLEAN DEFAULT 0",
            "salary_confidence": "FLOAT",
            "employment_type": "VARCHAR(80)",
            "required_skills": "TEXT",
            "source_posting_id": "VARCHAR(255)",
            "url": "TEXT",
            "application_url": "TEXT",
            "company_career_url": "TEXT",
            "remote_status": "VARCHAR(50)",
            "role_type": "VARCHAR(120)",
            "occupation_group": "VARCHAR(255)",
            "experience_level": "VARCHAR(80)",
            "source_legal_basis": "TEXT",
            "ingestion_batch_id": "VARCHAR(120)",
            "posted_at": "DATETIME",
            "expires_at": "DATETIME",
            "last_seen_at": "DATETIME",
            "is_expired": "BOOLEAN NOT NULL DEFAULT 0",
        }
        with self.engine.begin() as connection:
            rows = connection.execute(text("PRAGMA table_info(job_postings)")).fetchall()
            existing = {row[1] for row in rows}
            for column, column_type in expected_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE job_postings ADD COLUMN {column} {column_type}"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS ingestion_batches (
                    id VARCHAR PRIMARY KEY,
                    source TEXT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    fetched_count INTEGER DEFAULT 0,
                    saved_count INTEGER DEFAULT 0,
                    expired_count INTEGER DEFAULT 0,
                    started_at DATETIME NOT NULL,
                    finished_at DATETIME,
                    error_message TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ingestion_batch_status ON ingestion_batches(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ingestion_batch_started_at ON ingestion_batches(started_at)"))
    
    def drop_tables(self):
        """Drop all database tables."""
        from .models import Base
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("Database tables dropped")
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
        logger.info("Database connection closed")


# Global database instance
_db_instance = None


def init_database(database_url: str) -> Database:
    """Initialize global database instance.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Database instance
    """
    global _db_instance
    _db_instance = Database(database_url)
    return _db_instance


def get_database() -> Database:
    """Get global database instance.
    
    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_instance
