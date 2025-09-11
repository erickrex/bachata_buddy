"""
SQLite database configuration and session management for the Bachata Choreography Generator.
"""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session


# Database configuration
DATABASE_DIR = Path(__file__).parent.parent / "data"
DATABASE_PATH = DATABASE_DIR / "database.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure data directory exists
DATABASE_DIR.mkdir(exist_ok=True)

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Allow SQLite to be used with FastAPI
    echo=False  # Set to True for SQL query logging during development
)

# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints and other SQLite optimizations."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and performance
    cursor.execute("PRAGMA cache_size=1000")  # Increase cache size
    cursor.execute("PRAGMA temp_store=MEMORY")  # Store temporary tables in memory
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()


def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency function to get database session for FastAPI endpoints.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """
    Initialize the database by creating all tables.
    This should be called during application startup.
    """
    Base.metadata.create_all(bind=engine)


def get_database_info() -> dict:
    """
    Get information about the database for monitoring and debugging.
    
    Returns:
        dict: Database information including path, size, and connection status
    """
    try:
        db_size = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0
        return {
            "database_path": str(DATABASE_PATH),
            "database_exists": DATABASE_PATH.exists(),
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "connection_url": DATABASE_URL
        }
    except Exception as e:
        return {
            "database_path": str(DATABASE_PATH),
            "error": str(e)
        }