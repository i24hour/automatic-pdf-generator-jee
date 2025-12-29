"""
Celery tasks for background processing.
PDF generation task that runs asynchronously.
"""

import os
import sys
import base64
from datetime import datetime, timezone

# Ensure the app directory is in Python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Now import models after path is set
from models import JobStatus
from services.llm_engine import llm_engine
from services.pdf_engine import pdf_engine

# Database setup for worker
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Get a database session for the worker."""
    return SessionLocal()


@celery_app.task(bind=True)
def generate_pdf_task(self, job_id: str, subject: str, topic: str, level: str, question_count: int):
    """
    Background task to generate PDF.
    Updates JobStatus in database as it progresses.
    """
    db = get_db_session()
    
    try:
        # Update status to processing
        job = db.query(JobStatus).filter(JobStatus.id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        job.status = "processing"
        job.progress = 10
        db.commit()
        
        # Step 1: Generate questions using LLM (50% of work)
        job.progress = 20
        db.commit()
        
        questions = llm_engine.generate_questions(
            subject=subject,
            topic=topic,
            level=level,
            count=question_count
        )
        
        if not questions or "error" in questions:
            job.status = "failed"
            job.error_message = questions.get("error", "Failed to generate questions")
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"error": job.error_message}
        
        job.progress = 60
        db.commit()
        
        # Step 2: Generate PDF (40% of work)
        pdf_result = pdf_engine.generate_pdf(
            questions=questions,
            subject=subject,
            topic=topic,
            level=level
        )
        
        if not pdf_result or "error" in pdf_result:
            job.status = "failed"
            job.error_message = pdf_result.get("error", "Failed to generate PDF")
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"error": job.error_message}
        
        job.progress = 90
        db.commit()
        
        # Step 3: Encode PDF and save
        pdf_path = pdf_result.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                job.pdf_data = base64.b64encode(pdf_bytes).decode("utf-8")
            job.pdf_filename = os.path.basename(pdf_path)
            # Clean up the file after encoding
            try:
                os.remove(pdf_path)
            except:
                pass
        
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        return {"success": True, "job_id": job_id}
        
    except Exception as e:
        job = db.query(JobStatus).filter(JobStatus.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()
