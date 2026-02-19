import os
from database import engine, Base
from models import APIUsageLog

def migrate():
    print("Creating api_usage_logs table...")
    # This will only create tables that don't exist
    Base.metadata.create_all(bind=engine)
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
