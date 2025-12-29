"""
Mentors Mantra Test Generator - FastAPI Backend
Main application entry point with API endpoints.
"""

import os
import uuid
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from services.llm_engine import llm_engine
from services.pdf_engine import pdf_engine
from database import get_db, init_db
from models import User, PDFGeneration, JobStatus
from auth import get_current_user_required, get_current_user
from routers.auth_router import router as auth_router

# Load environment variables
load_dotenv()

# Rate limiting configuration
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "3"))
RATE_LIMIT_HOURS = int(os.getenv("RATE_LIMIT_HOURS", "6"))

# Initialize FastAPI app
app = FastAPI(
    title="Mentors Mantra Test Generator",
    description="Generate professionally formatted PDF test papers using AI",
    version="2.0.0"
)

# Configure CORS
origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "https://mentors-mantra-test-generator.vercel.app",
    "https://*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include auth router
app.include_router(auth_router)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for test generation."""
    subject: str = Field(..., description="Subject: Physics, Chemistry, or Maths")
    topic: str = Field(..., description="Specific topic for the test")
    total_questions: int = Field(default=20, ge=5, le=50, description="Total number of questions")
    level: str = Field(default="JEE Mains", description="Difficulty level: Boards, JEE Mains, JEE Advanced, Olympiad")


class GenerateResponse(BaseModel):
    """Response model for successful generation."""
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    total_mcq: int = 0
    total_numerical: int = 0
    rate_limit_remaining: int = 0
    rate_limit_reset_hours: float = 0


class RateLimitInfo(BaseModel):
    """Rate limit information."""
    limit: int
    remaining: int
    reset_hours: float
    used: int


class ErrorResponse(BaseModel):
    """Response model for errors."""
    success: bool = False
    error: str


class JobSubmitResponse(BaseModel):
    """Response when a job is submitted."""
    success: bool
    job_id: str
    message: str
    rate_limit_remaining: int = 0


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0
    error_message: Optional[str] = None
    pdf_ready: bool = False



def check_rate_limit(user: User, db: Session) -> tuple[bool, int, float]:
    """
    Check if user has exceeded rate limit.
    Returns: (is_allowed, remaining_count, hours_until_reset)
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=RATE_LIMIT_HOURS)
    
    # Count generations in the rate limit window
    recent_generations = db.query(PDFGeneration).filter(
        PDFGeneration.user_id == user.id,
        PDFGeneration.created_at >= cutoff_time
    ).order_by(PDFGeneration.created_at.asc()).all()
    
    used_count = len(recent_generations)
    remaining = max(0, RATE_LIMIT_COUNT - used_count)
    
    # Calculate reset time (when the oldest generation expires)
    if recent_generations and used_count >= RATE_LIMIT_COUNT:
        oldest = recent_generations[0]
        reset_time = oldest.created_at + timedelta(hours=RATE_LIMIT_HOURS)
        hours_until_reset = (reset_time - datetime.now(timezone.utc)).total_seconds() / 3600
        hours_until_reset = max(0, hours_until_reset)
    else:
        hours_until_reset = 0
    
    is_allowed = used_count < RATE_LIMIT_COUNT
    return is_allowed, remaining, hours_until_reset


def record_generation(user: User, request: GenerateRequest, pdf_filename: str, db: Session):
    """Record a PDF generation for rate limiting."""
    generation = PDFGeneration(
        user_id=user.id,
        subject=request.subject,
        topic=request.topic,
        level=request.level,
        question_count=request.total_questions,
        pdf_filename=pdf_filename
    )
    db.add(generation)
    db.commit()


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Mentors Mantra Test Generator",
        "version": "2.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "active_model": os.getenv("ACTIVE_MODEL", "not configured"),
        "services": {
            "llm_engine": "ready",
            "pdf_engine": "ready"
        }
    }


@app.get("/api/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get current rate limit status."""
    is_allowed, remaining, reset_hours = check_rate_limit(current_user, db)
    
    return RateLimitInfo(
        limit=RATE_LIMIT_COUNT,
        remaining=remaining,
        reset_hours=round(reset_hours, 2),
        used=RATE_LIMIT_COUNT - remaining
    )


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_test(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Generate a test paper PDF.
    
    Requires authentication. Limited to 3 PDFs per 6 hours.
    """
    # Check rate limit
    is_allowed, remaining, reset_hours = check_rate_limit(current_user, db)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You can generate {RATE_LIMIT_COUNT} PDFs every {RATE_LIMIT_HOURS} hours. Try again in {reset_hours:.1f} hours."
        )
    
    try:
        # Calculate question split: 80% MCQ, 20% Numerical
        mcq_count = int(request.total_questions * 0.8)
        numerical_count = request.total_questions - mcq_count
        
        # Ensure at least 1 of each type
        if mcq_count < 1:
            mcq_count = 1
        if numerical_count < 1:
            numerical_count = 1
            mcq_count = request.total_questions - 1
        
        # Generate questions using LLM
        llm_result = llm_engine.generate_questions(
            subject=request.subject,
            topic=request.topic,
            mcq_count=mcq_count,
            numerical_count=numerical_count,
            level=request.level
        )
        
        if not llm_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=llm_result.get("error", "Failed to generate questions")
            )
        
        # Generate unique filename
        filename = f"test_{request.subject}_{request.topic}_{uuid.uuid4().hex[:8]}"
        filename = filename.replace(" ", "_").lower()
        
        # Generate PDF
        pdf_path = pdf_engine.generate_pdf(llm_result, filename)
        
        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF. Please check if pdflatex is installed."
            )
        
        # Record this generation for rate limiting
        record_generation(current_user, request, os.path.basename(pdf_path), db)
        
        # Get updated rate limit info
        _, new_remaining, new_reset_hours = check_rate_limit(current_user, db)
        
        return GenerateResponse(
            success=True,
            message="Test paper generated successfully",
            pdf_filename=os.path.basename(pdf_path),
            total_mcq=mcq_count,
            total_numerical=numerical_count,
            rate_limit_remaining=new_remaining,
            rate_limit_reset_hours=round(new_reset_hours, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def download_pdf(filename: str):
    """
    Download a generated PDF file.
    
    - **filename**: The PDF filename returned from /api/generate
    """
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    pdf_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf"
    )


# ============== Background Job Endpoints ==============

@app.post("/api/job/submit", response_model=JobSubmitResponse)
async def submit_job(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Submit a PDF generation job (async).
    Returns immediately with a job ID to poll for status.
    """
    from tasks import generate_pdf_task
    
    # Check rate limit
    is_allowed, remaining, reset_hours = check_rate_limit(current_user, db)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_hours:.1f} hours."
        )
    
    # Create job record
    job = JobStatus(
        user_id=current_user.id,
        subject=request.subject,
        topic=request.topic,
        level=request.level,
        question_count=request.total_questions,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Record generation for rate limiting
    generation = PDFGeneration(
        user_id=current_user.id,
        subject=request.subject,
        topic=request.topic,
        level=request.level,
        question_count=request.total_questions
    )
    db.add(generation)
    db.commit()
    
    # Queue the background task
    generate_pdf_task.delay(
        job_id=job.id,
        subject=request.subject,
        topic=request.topic,
        level=request.level,
        question_count=request.total_questions
    )
    
    # Get updated rate limit
    _, new_remaining, _ = check_rate_limit(current_user, db)
    
    return JobSubmitResponse(
        success=True,
        job_id=job.id,
        message="Job submitted. Poll /api/job/{job_id}/status for progress.",
        rate_limit_remaining=new_remaining
    )


@app.get("/api/job/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Check the status of a PDF generation job."""
    job = db.query(JobStatus).filter(
        JobStatus.id == job_id,
        JobStatus.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        pdf_ready=job.status == "completed" and job.pdf_data is not None
    )


@app.get("/api/job/{job_id}/download")
async def download_job_pdf(
    job_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Download the PDF for a completed job."""
    from fastapi.responses import Response
    
    job = db.query(JobStatus).filter(
        JobStatus.id == job_id,
        JobStatus.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.pdf_data:
        raise HTTPException(status_code=404, detail="PDF data not found")
    
    # Decode base64 PDF
    pdf_bytes = base64.b64decode(job.pdf_data)
    
    filename = job.pdf_filename or f"test_{job.subject}_{job.topic}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



@app.get("/api/models")
async def list_models():
    """List available LLM models."""
    return {
        "active_model": os.getenv("ACTIVE_MODEL", "gemini/gemini-1.5-flash"),
        "available_models": [
            "gemini/gemini-1.5-flash",
            "gemini/gemini-1.5-pro",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3-sonnet-20240229",
            "anthropic/claude-3-haiku-20240307"
        ]
    }


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
