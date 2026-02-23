"""
Database configuration and session management.
Uses SQLite for local development, PostgreSQL for production.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - SQLite for local development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Heroku uses postgres:// but SQLAlchemy 1.4+ requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
# For SQLite, we need connect_args to allow multi-threading
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL for production
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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
    from models import (
        User,
        PDFGeneration,
        RefreshToken,
        VerificationToken,
        PasswordResetToken,
        JobStatus,
        TopicSubjectCache,
        SharedPDF,
        PDFLike,
        UserBadge,
        PaymentOrder,
        UserSubscription,
    )  # Import here to avoid circular imports
    Base.metadata.create_all(bind=engine)

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # --- existing migrations ---
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50)"))
                conn.commit()
            except Exception:
                conn.rollback()

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN total_posts INTEGER DEFAULT 0"))
                conn.commit()
            except Exception:
                conn.rollback()

            # --- payment / subscription migrations ---
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE"))
                conn.commit()
            except Exception:
                conn.rollback()

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN plan VARCHAR(20) DEFAULT 'free'"))
                conn.commit()
            except Exception:
                conn.rollback()

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
                conn.commit()
            except Exception:
                conn.rollback()

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN class_grade VARCHAR(20)"))
                conn.commit()
            except Exception:
                conn.rollback()

    except Exception as e:
        print(f"Migration warning (can be ignored if columns exist): {e}")
