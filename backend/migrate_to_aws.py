
import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base, User, PDFGeneration, PromoCode, PromoCodeUsage, RefreshToken, VerificationToken, PasswordResetToken, TopicSubjectCache, InstituteUser, InstituteGeneration
from dotenv import load_dotenv

# Load env vars
load_dotenv()

def migrate_data(source_url, target_url):
    print(f"Source: {source_url.split('@')[-1]}")
    print(f"Target: {target_url.split('@')[-1]}")
    
    # Create engines
    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)
    
    # Create tables in target
    print("Creating tables in target database...")
    Base.metadata.create_all(target_engine)
    
    # Create sessions
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)
    
    source_session = SourceSession()
    target_session = TargetSession()
    
    # Models to migrate in order of dependency
    models = [
        User, 
        InstituteUser,
        PromoCode, 
        RefreshToken, 
        VerificationToken, 
        PasswordResetToken,
        TopicSubjectCache,
        PDFGeneration, 
        InstituteGeneration,
        PromoCodeUsage
    ]
    
    try:
        for model in models:
            table_name = model.__tablename__
            print(f"Migrating table: {table_name}...")
            
            # Get all records from source
            records = source_session.query(model).all()
            count = len(records)
            print(f"  Found {count} records.")
            
            if count > 0:
                # Check if target already has data
                target_count = target_session.query(model).count()
                if target_count > 0:
                    print(f"  Target table {table_name} already has {target_count} records. Skipping to avoid duplicates.")
                    continue
                
                # Copy records
                for record in records:
                    target_session.merge(record)
                
                target_session.commit()
                print(f"  Migrated {count} records.")
            
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nError during migration: {e}")
        target_session.rollback()
    finally:
        source_session.close()
        target_session.close()

if __name__ == "__main__":
    # Get source URL from existing env or input
    source_db_url = os.getenv("DATABASE_URL")
    
    # Ask for AWS RDS URL
    if len(sys.argv) > 1:
        target_db_url = sys.argv[1]
    else:
        print("Usage: python migrate_to_aws.py <aws_rds_connection_string>")
        print("Or set TARGET_DATABASE_URL env var")
        target_db_url = input("Enter AWS RDS Connection String: ")
    
    if not source_db_url:
        print("Error: DATABASE_URL (Source) not found in environment.")
        exit(1)
        
    if not target_db_url:
        print("Error: Target URL not provided.")
        exit(1)
        
    # Fix postgres:// for SQLAlchemy
    if source_db_url.startswith("postgres://"):
        source_db_url = source_db_url.replace("postgres://", "postgresql://", 1)
    if target_db_url.startswith("postgres://"):
        target_db_url = target_db_url.replace("postgres://", "postgresql://", 1)
        
    migrate_data(source_db_url, target_db_url)
