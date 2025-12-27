"""
Database configuration and session management.
Uses SQLite for simplicity (can be upgraded to PostgreSQL).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Create engine
# For SQLite, we need connect_args to allow multi-threading
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from models import User, PDFGeneration  # Import here to avoid circular imports
    Base.metadata.create_all(bind=engine)
