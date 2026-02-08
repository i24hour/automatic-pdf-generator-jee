
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend/.env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def check_posts():
    try:
        with engine.connect() as conn:
            # check if table exists first
            result = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_name = 'shared_pdfs'"))
            if result.scalar() == 0:
                print("Table 'shared_pdfs' does not exist.")
                return

            result = conn.execute(text("SELECT count(*) FROM shared_pdfs"))
            count = result.scalar()
            print(f"Total Shared PDFs: {count}")
            
            # Check visibility stats
            stats = conn.execute(text("SELECT visibility, count(*) FROM shared_pdfs GROUP BY visibility")).fetchall()
            print("Visibility stats:")
            for s in stats:
                print(f" - {s[0]}: {s[1]}")

            # Check valid URLs
            valid_count = conn.execute(text("SELECT count(*) FROM shared_pdfs WHERE pdf_url != 'pending'")).scalar()
            print(f"Valid URLs excluding 'pending': {valid_count}")

            if count > 0:
                print("\nSample VALID PDF URLs:")
                posts = conn.execute(text("SELECT id, topic, visibility, pdf_url FROM shared_pdfs WHERE pdf_url != 'pending' LIMIT 5")).fetchall()
                for p in posts:
                    print(f" - {p}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_posts()
