import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import PromoCode, PDFGeneration
from dotenv import load_dotenv

# Load env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///backend/app.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed():
    db = SessionLocal()
    try:
        # 1. Create Promo Code
        code = "MENTORSMANTRA6"
        existing = db.query(PromoCode).filter(PromoCode.code == code).first()
        if not existing:
            print(f"Creating promo code {code}...")
            promo = PromoCode(
                code=code,
                bonus_limit=6,
                max_uses=5,
                is_monthly_only=True,
                is_active=True
            )
            db.add(promo)
            print("Promo code created.")
        else:
            print(f"Promo code {code} already exists. Updating...")
            existing.bonus_limit = 6
            existing.max_uses = 5
            existing.is_monthly_only = True
            existing.is_active = True
            print("Promo code updated.")
        
        # 2. Reset Usage (Delete PDFGenerations for current month)
        print("Resetting usage for current month...")
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        deleted = db.query(PDFGeneration).filter(
            PDFGeneration.created_at >= start_of_month
        ).delete(synchronize_session=False)
        
        print(f"Deleted {deleted} PDF generation records from this month.")
        
        db.commit()
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
