import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found.")
else:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        try:
            # For every user, zero out their bonus limit if it came from promo codes.
            # We assume ALL current bonus limits > 0 are from promo codes for this app.
            conn.execute(text("UPDATE users SET bonus_limit = 0, monthly_bonus_limit = 0 WHERE bonus_limit > 0 OR monthly_bonus_limit > 0;"))
            conn.commit()
            print("Successfully migrated all users to dynamic promo limits!")
        except Exception as e:
            print("Error:", e)
