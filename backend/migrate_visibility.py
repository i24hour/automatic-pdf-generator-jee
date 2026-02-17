import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Ensure we can import from current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL

def migrate():
    print("Starting Visibility Migration...")
    
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('tests')]
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Add New Columns if they don't exist
            if 'visibility_type' not in columns:
                print("Adding visibility_type column...")
                conn.execute(text("ALTER TABLE tests ADD COLUMN visibility_type VARCHAR"))
                
            if 'status' not in columns:
                print("Adding status column...")
                conn.execute(text("ALTER TABLE tests ADD COLUMN status VARCHAR"))
                
            if 'classroom_id' not in columns:
                print("Adding classroom_id column...")
                conn.execute(text("ALTER TABLE tests ADD COLUMN classroom_id VARCHAR"))
                
            if 'share_code' not in columns:
                print("Adding share_code column...")
                conn.execute(text("ALTER TABLE tests ADD COLUMN share_code VARCHAR"))
                
            if 'is_featured' not in columns:
                print("Adding is_featured column...")
                conn.execute(text("ALTER TABLE tests ADD COLUMN is_featured BOOLEAN DEFAULT 0"))
                
            if 'is_generated_practice' not in columns:
                print("Adding is_generated_practice column...")
                conn.execute(text("ALTER TABLE tests ADD COLUMN is_generated_practice BOOLEAN DEFAULT 0"))

            # 2. Data Migration
            print("Migrating existing data...")
            
            # If is_public was True -> COMMUNITY, PUBLISHED
            conn.execute(text("""
                UPDATE tests 
                SET visibility_type = 'COMMUNITY', status = 'published' 
                WHERE is_public = 1
            """))
            
            # If is_public was False -> PRIVATE, PUBLISHED, IS_GENERATED_PRACTICE=True
            conn.execute(text("""
                UPDATE tests 
                SET visibility_type = 'PRIVATE', status = 'published', is_generated_practice = 1 
                WHERE is_public = 0 OR is_public IS NULL
            """))
            
            # Set defaults for new rows if any nulls remain
            conn.execute(text("UPDATE tests SET visibility_type = 'PRIVATE' WHERE visibility_type IS NULL"))
            conn.execute(text("UPDATE tests SET status = 'published' WHERE status IS NULL"))
            conn.execute(text("UPDATE tests SET is_featured = 0 WHERE is_featured IS NULL"))
            conn.execute(text("UPDATE tests SET is_generated_practice = 0 WHERE is_generated_practice IS NULL"))

            # 3. Create Indexes (SQLite syntax)
            print("Creating Indexes...")
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tests_visibility_type ON tests (visibility_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tests_status ON tests (status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tests_classroom_id ON tests (classroom_id)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_tests_share_code ON tests (share_code)"))
                # Composite index
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_test_visibility_status ON tests (visibility_type, status)"))
            except Exception as e:
                print(f"Index creation warning (might already exist): {e}")

            # 4. cleanup old column (SQLite doesn't support DROP COLUMN easily in older versions, but we can try)
            # For safety in this environment, we might skip strict DROP COLUMN or do it if supported.
            # Modern SQLite supports it.
            if 'is_public' in columns:
                print("Dropping is_public column...")
                try:
                    conn.execute(text("ALTER TABLE tests DROP COLUMN is_public"))
                except Exception as e:
                    print(f"Could not drop column 'is_public' (SQLite limitation?): {e}")
                    print("Ignoring drop column error. Data is safe.")

            trans.commit()
            print("Migration Completed Successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"Migration Failed: {e}")
            raise e

if __name__ == "__main__":
    migrate()
