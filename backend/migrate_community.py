"""
Migration script to add PDF Community tables and columns.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def run_migration():
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        print("Starting migration...")
        
        # 1. Add columns to users table
        try:
            print("Adding columns to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR UNIQUE"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_likes_received INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_posts INTEGER DEFAULT 0"))
            print("Users table updated.")
        except Exception as e:
            print(f"Error updating users table: {e}")

        # 2. Create shared_pdfs table
        try:
            print("Creating shared_pdfs table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS shared_pdfs (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    pdf_url VARCHAR NOT NULL,
                    pdf_filename VARCHAR NOT NULL,
                    caption TEXT,
                    subject VARCHAR NOT NULL,
                    topic VARCHAR NOT NULL,
                    level VARCHAR NOT NULL,
                    difficulty VARCHAR NOT NULL,
                    question_count INTEGER DEFAULT 0,
                    has_solutions BOOLEAN DEFAULT FALSE,
                    visibility VARCHAR DEFAULT 'private',
                    download_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            print("shared_pdfs table created.")
        except Exception as e:
            print(f"Error creating shared_pdfs table: {e}")

        # 3. Create pdf_likes table
        try:
            print("Creating pdf_likes table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pdf_likes (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    shared_pdf_id VARCHAR NOT NULL REFERENCES shared_pdfs(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT uq_user_pdf_like UNIQUE (user_id, shared_pdf_id)
                )
            """))
            print("pdf_likes table created.")
        except Exception as e:
            print(f"Error creating pdf_likes table: {e}")

        # 4. Create user_badges table
        try:
            print("Creating user_badges table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_badges (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    badge_type VARCHAR NOT NULL,
                    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT uq_user_badge UNIQUE (user_id, badge_type)
                )
            """))
            print("user_badges table created.")
        except Exception as e:
            print(f"Error creating user_badges table: {e}")

        print("Migration complete!")

if __name__ == "__main__":
    run_migration()
