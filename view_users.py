import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Database URL from Cloud Run
DATABASE_URL = "postgres://ucd72m93379gcf:p07ce434028dd0062adcaf323a52306a9affc5f81f0e8c9fb688a9cd9f194cdca@c85cgnr0vdhse3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dcu79snd465pup"

# Fix for SQLAlchemy (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def view_users():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Query users
            result = conn.execute(text("SELECT email, name, phone, bonus_limit, created_at FROM users ORDER BY created_at DESC"))
            
            print("\n=== 👥 USERS IN DATABASE ===")
            print(f"{'EMAIL':<30} | {'NAME':<20} | {'PHONE':<15} | {'BONUS':<5} | {'CREATED AT'}")
            print("-" * 100)
            
            count = 0
            for row in result:
                count += 1
                email = row[0]
                name = row[1] if row[1] else "N/A"
                phone = row[2] if row[2] else "N/A"
                bonus = row[3]
                created = str(row[4])[:19]
                
                print(f"{email:<30} | {name:<20} | {phone:<15} | {bonus:<5} | {created}")
            
            print(f"\nTotal Users: {count}")
            
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    view_users()
