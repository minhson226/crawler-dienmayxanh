"""Database session and connection management."""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from dmx.db.models import Base
from dmx.utils.config import get_config

# Global variables
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_database_url() -> str:
    """Get database URL from environment or config."""
    # Check environment variable first
    db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    
    if db_url:
        return db_url
    
    # Default to SQLite for development
    db_path = os.path.join(os.getcwd(), "dmx.sqlite")
    return f"sqlite:///{db_path}"


def create_database_engine() -> Engine:
    """Create database engine with appropriate configuration."""
    db_url = get_database_url()
    
    # Configure engine based on database type
    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            echo=False,  # Set to True for SQL debug logging
            connect_args={"check_same_thread": False},
        )
    elif db_url.startswith("postgresql"):
        engine = create_engine(
            db_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )
    else:
        # Generic configuration
        engine = create_engine(db_url, echo=False)
    
    return engine


def init_db(drop_existing: bool = False) -> None:
    """Initialize database with tables and indexes."""
    global _engine, _session_factory
    
    _engine = create_database_engine()
    
    if drop_existing:
        Base.metadata.drop_all(_engine)
    
    # Create all tables
    Base.metadata.create_all(_engine)
    
    # Create session factory
    _session_factory = sessionmaker(bind=_engine)
    
    print(f"Database initialized: {get_database_url()}")


def get_engine() -> Engine:
    """Get database engine, initializing if necessary."""
    global _engine
    
    if _engine is None:
        _engine = create_database_engine()
    
    return _engine


def get_session_factory() -> sessionmaker:
    """Get session factory, initializing if necessary."""
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_session() -> Session:
    """Create a new database session (manual management)."""
    session_factory = get_session_factory()
    return session_factory()


def health_check() -> bool:
    """Check database connection health."""
    try:
        with get_session() as session:
            # Simple query to test connection
            session.execute("SELECT 1")
            return True
    except Exception:
        return False


def get_db_info() -> dict:
    """Get database information."""
    engine = get_engine()
    
    return {
        "url": str(engine.url).replace(engine.url.password or "", "***"),
        "driver": engine.dialect.name,
        "pool_size": getattr(engine.pool, "size", "N/A"),
        "checked_out": getattr(engine.pool, "checkedout", "N/A"),
    }