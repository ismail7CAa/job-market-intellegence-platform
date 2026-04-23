"""Database connection and session management."""

from sqlalchemy import create_engine
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
        logger.info("Database tables created")
    
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
