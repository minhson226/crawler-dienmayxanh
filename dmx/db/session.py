"""
Database session management
"""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from .models import Base
import logging

logger = logging.getLogger(__name__)


class _SessionContext:
    """Context manager for database sessions"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
                logger.error(f"Database session error: {exc_val}")
        finally:
            self.session.close()


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = None):
        """Initialize database manager"""
        self.database_url = database_url or os.getenv(
            "DB_URL", "sqlite:///dmx.sqlite"
        )
        
        # Configure engine based on database type
        if self.database_url.startswith("sqlite"):
            self.engine = create_engine(
                self.database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=os.getenv("DB_ECHO", "false").lower() == "true"
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                self.database_url,
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
                echo=os.getenv("DB_ECHO", "false").lower() == "true"
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        
    def create_tables(self) -> None:
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def drop_tables(self) -> None:
        """Drop all database tables"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    def get_session_context(self):
        """Get database session as context manager"""
        return _SessionContext(self.get_session())


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(database_url: str = None) -> DatabaseManager:
    """Initialize database with custom URL"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


def get_session() -> Session:
    """Get database session"""
    return get_db_manager().get_session()


def get_session_context():
    """Get database session context manager"""
    return get_db_manager().get_session_context()


def create_tables():
    """Create all database tables"""
    get_db_manager().create_tables()


def drop_tables():
    """Drop all database tables"""
    get_db_manager().drop_tables()