import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found.")
else:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE pdf_generations ADD COLUMN IF NOT EXISTS is_institute BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added is_institute to pdf_generations!")
        except Exception as e:
            print("Error:", e)
