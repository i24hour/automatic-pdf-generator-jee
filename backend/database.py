"""
Database configuration and session management.
Uses SQLite for local development, PostgreSQL for production.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


# Database URL - AWS RDS PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Handle Heroku/Render postgres:// format if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine for PostgreSQL
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_recycle=300
)


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
    """Initialize database tables and run migrations."""
    from models import (
        User,
        PDFGeneration,
        PromoCode,
        PromoCodeUsage,
        RefreshToken,
        VerificationToken,
        PasswordResetToken,
        TopicSubjectCache,
        SystemErrorLog,
        TestAttempt,
        QuestionResponse,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Run migrations for new columns (safe to run multiple times)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Add bonus_limit column to users if it doesn't exist
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN bonus_limit INTEGER DEFAULT 0"))
                conn.commit()
            except Exception:
                conn.rollback()
            
            # Add phone column to users if it doesn't exist
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
                conn.commit()
            except Exception:
                conn.rollback()
            
            # Add expires_at column to promo_codes if it doesn't exist
            try:
                conn.execute(text("ALTER TABLE promo_codes ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE"))
                conn.commit()
            except Exception:
                conn.rollback()

            # Add total_posts to users
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN total_posts INTEGER DEFAULT 0"))
                conn.commit()
            except Exception:
                conn.rollback()

            # Add total_likes_received to users
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN total_likes_received INTEGER DEFAULT 0"))
                conn.commit()
            except Exception:
                conn.rollback()

            # Add monthly_bonus_limit to users
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN monthly_bonus_limit INTEGER DEFAULT 0"))
                conn.commit()
            except Exception:
                conn.rollback()

            # Add last_bonus_month to users
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_bonus_month VARCHAR(10)"))
                conn.commit()
            except Exception:
                conn.rollback()
            
            # Add fresh_questions_enabled to users (default=True)
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN fresh_questions_enabled BOOLEAN DEFAULT TRUE"))
                conn.commit()
            except Exception:
                conn.rollback()
            
            # Add slug to shared_pdfs for unlisted access
            try:
                conn.execute(text("ALTER TABLE shared_pdfs ADD COLUMN slug VARCHAR(50) UNIQUE"))
                conn.commit()
            except Exception:
                conn.rollback()
            
            # Create user_question_history table if not exists
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_question_history (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        topic VARCHAR NOT NULL,
                        level VARCHAR NOT NULL,
                        question_text TEXT NOT NULL,
                        question_hash VARCHAR(32) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        CONSTRAINT uq_user_topic_question UNIQUE (user_id, topic, level, question_hash)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_uqh_user_id ON user_question_history(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_uqh_topic ON user_question_history(topic)"))
                conn.commit()
            except Exception:
                conn.rollback()

            # Add diagram_json to question_responses if it doesn't exist
            try:
                conn.execute(text("ALTER TABLE question_responses ADD COLUMN diagram_json TEXT"))
                conn.commit()
            except Exception:
                conn.rollback()
                
    except Exception as e:
        print(f"Migration warning (can be ignored if columns exist): {e}")

    # Add username to users if it doesn't exist
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
                conn.commit()
            except Exception:
                conn.rollback()
    except Exception as e:
        print(f"Migration warning (username): {e}")

    # Add class_grade to users if it doesn't exist
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN class_grade VARCHAR"))
                conn.commit()
            except Exception:
                conn.rollback()
    except Exception as e:
        print(f"Migration warning (class_grade): {e}")

