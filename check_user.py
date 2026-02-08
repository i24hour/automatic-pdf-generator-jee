
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

def check_user(email):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, email, username FROM users WHERE email = :email"), {"email": email}).fetchone()
        if result:
            print(f"User Found: ID={result[0]}, Email={result[1]}, Username={result[2]}")
        else:
            print("User not found")

if __name__ == "__main__":
    check_user("priyanshu85953@gmail.com")
