
import sys
from sqlalchemy import create_engine, text

def check_dbs(url):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false;"))
            dbs = [row[0] for row in result]
            print(f"Connected! Available databases: {dbs}")
            
            # Try to create infinitest if not exists
            if 'infinitest' not in dbs:
                print("Creating 'infinitest' database...")
                # Cannot run CREATE DATABASE inside a transaction block usually, 
                # so we need to set isolation level to AUTOCOMMIT
                connection = engine.raw_connection()
                connection.set_isolation_level(0)
                cursor = connection.cursor()
                cursor.execute("CREATE DATABASE infinitest")
                print("Created 'infinitest' database successfully!")
                cursor.close()
                connection.close()
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    url = sys.argv[1]
    check_dbs(url)
