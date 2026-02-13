import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Connection Deets
DB_HOST = "infinitest.cuf8es4uybc1.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "infinitest"
DB_USER = "postgres"
DB_PASS = "priyanshuaws123"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def check_connection():
    print(f"Testing connection to: {DB_HOST}...")
    try:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 10})
        connection = engine.connect()
        print("✅ Connection Successful!")
        connection.close()
        return True
    except OperationalError as e:
        print(f"❌ Connection Failed: {e}")
        return False
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    check_connection()
