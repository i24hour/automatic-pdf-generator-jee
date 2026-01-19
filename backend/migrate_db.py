import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Use absolute path
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
print(f"Loading env from: {env_path}")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///backend/app.db")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    exit(1)

# Fix for postgres URL if needed (sqlalchemy requires postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def run_migration():
    with engine.connect() as conn:
        print("Adding monthly_bonus_limit to users...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN monthly_bonus_limit INTEGER DEFAULT 0"))
            print("Success.")
        except Exception as e:
            print(f"Skipped (maybe exists): {e}")

        print("Adding last_bonus_month to users...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_bonus_month VARCHAR"))
            print("Success.")
        except Exception as e:
            print(f"Skipped (maybe exists): {e}")

        print("Adding is_monthly_only to promo_codes...")
        try:
            conn.execute(text("ALTER TABLE promo_codes ADD COLUMN is_monthly_only BOOLEAN DEFAULT FALSE"))
            print("Success.")
        except Exception as e:
            print(f"Skipped (maybe exists): {e}")
            
        print("Adding class_grade to users...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN class_grade VARCHAR"))
            print("Success.")
        except Exception as e:
            print(f"Skipped (maybe exists): {e}")
            
        conn.commit()

if __name__ == "__main__":
    run_migration()
