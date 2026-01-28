"""
Mentors Mantra Test Generator - FastAPI Backend
Main application entry point with API endpoints.
"""

import os
import uuid
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from services.llm_engine import llm_engine, get_user_question_history, save_question_history
from services.pdf_engine import pdf_engine
from database import get_db, init_db
from models import User, PDFGeneration, PromoCode, PromoCodeUsage, TopicSubjectCache, SharedPDF, SystemErrorLog
from auth import get_current_user_required, get_current_user
from routers.auth_router import router as auth_router
from routers.institute_router import router as institute_router
from routers.posts_router import router as posts_router
from routers.pdf_router import router as pdf_router
from services.email_service import email_service
# from services.r2_storage import r2_storage  # Deprecated
from services.gcs_storage import gcs_storage
from services.job_store import job_store, JobStatus

# Load environment variables
load_dotenv()

# Rate limiting configuration
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "8"))
RATE_LIMIT_HOURS = int(os.getenv("RATE_LIMIT_HOURS", "24"))

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
    "https://infinitest.tech",
    "https://www.infinitest.tech",
    "https://mentors-mantra-test-generator.vercel.app",
    "https://mentors-mantra-test-generator-git-main-priyanshu85953s-projects.vercel.app",
    "https://mentors-mantra-test-generator-*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(institute_router)
app.include_router(posts_router)
app.include_router(pdf_router)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()  # Run migrations for new columns


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for test generation."""
    subject: str = Field(..., description="Subject: Physics, Chemistry, or Maths")
    topic: str = Field(..., description="Specific topic for the test")
    total_questions: int = Field(default=20, ge=1, le=50, description="Total number of questions")
    level: str = Field(default="JEE Mains", description="Exam type: Boards, JEE Mains, JEE Advanced, Olympiad, NEET")
    difficulty: str = Field(default="Medium", description="Difficulty within exam: Easy, Medium, Hard")
    num_mcqs: Optional[int] = Field(default=None, description="Number of MCQs (optional)")
    num_numerical: Optional[int] = Field(default=None, description="Number of numerical questions (optional)")
    include_solutions: bool = Field(default=False, description="Include step-by-step solutions")
    # GATE Specific Fields
    gate_paper: Optional[str] = Field(default=None, description="GATE Paper Code (CSE, DA, etc.)")
    num_msq: Optional[int] = Field(default=None, description="Number of MSQs (GATE only)")
    num_nat: Optional[int] = Field(default=None, description="Number of NATs (GATE only)")
    num_ga: Optional[int] = Field(default=None, description="Number of General Aptitude questions (GATE only)")
    # Boards Specific Fields
    cbse_vsa: Optional[int] = Field(default=None, description="Number of Very Short Answer questions (Boards only)")
    cbse_sa: Optional[int] = Field(default=None, description="Number of Short Answer questions (Boards only)")
    cbse_la: Optional[int] = Field(default=None, description="Number of Long Answer questions (Boards only)")
    cbse_case: Optional[int] = Field(default=None, description="Number of Case Based questions (Boards only)")


class GenerateResponse(BaseModel):
    """Response model for successful generation."""
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    pdf_base64: Optional[str] = None  # Base64-encoded PDF for immediate download
    shared_pdf_id: Optional[str] = None  # ID for sharing/posting
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


class ApplyPromoRequest(BaseModel):
    """Request model for applying promo code."""
    code: str = Field(..., description="Promo code to apply")


class ApplyPromoResponse(BaseModel):
    """Response model for promo code application."""
    success: bool
    message: str
    new_limit: int = 0
    bonus_added: int = 0


class DetectSubjectRequest(BaseModel):
    """Request model for subject detection."""
    topic: str = Field(..., description="Topic to classify")


class DetectSubjectResponse(BaseModel):
    """Response model for subject detection."""
    subject: str
    confidence: str | float = "high"
    cached: bool = False


class ErrorLogRequest(BaseModel):
    """Request model for client-side error logging."""
    error_type: str = Field(..., description="Type of error (e.g. LOGIN_FAILURE, GENERATION_TIMEOUT)")
    error_details: str = Field(..., description="Detailed error message or stack trace")
    user_email: Optional[str] = None
    metadata_info: Optional[str] = None
    subject: str
    confidence: str = "high"
    cached: bool = False




def check_rate_limit(user: User, db: Session) -> tuple[bool, int, float]:
    """
    Check if user has exceeded rate limit.
    Returns: (is_allowed, remaining_count, hours_until_reset)
    """

    # Check if monthly bonus needs reset
    now = datetime.now(timezone.utc)
    current_month_str = now.strftime("%Y-%m")
    
    if user.last_bonus_month != current_month_str:
        user.monthly_bonus_limit = 0
        user.last_bonus_month = current_month_str
        db.commit()
        db.refresh(user)

    # User's total limit = base limit + permanent bonus + monthly bonus
    user_total_limit = RATE_LIMIT_COUNT + (user.bonus_limit or 0) + (user.monthly_bonus_limit or 0)
    
    # Calculate start of current month
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Count generations in the current month
    recent_generations = db.query(PDFGeneration).filter(
        PDFGeneration.user_id == user.id,
        PDFGeneration.created_at >= start_of_month
    ).all()
    
    used_count = len(recent_generations)
    remaining = max(0, user_total_limit - used_count)
    
    # Calculate reset time (1st of next month)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
    hours_until_reset = (next_month - now).total_seconds() / 3600
    
    is_allowed = used_count < user_total_limit
    return is_allowed, remaining, hours_until_reset, user_total_limit


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


@app.post("/api/detect-subject", response_model=DetectSubjectResponse)
async def detect_subject(request: DetectSubjectRequest, db: Session = Depends(get_db)):
    """
    Auto-detect the subject for a given topic using LLM.
    This helps users by automatically selecting the most likely subject.
    """
    if not request.topic or len(request.topic.strip()) < 2:
        return DetectSubjectResponse(subject="Physics", confidence="low", cached=False)

    normalized_topic = request.topic.strip().lower()

    cached_entry = db.query(TopicSubjectCache).filter(TopicSubjectCache.normalized_topic == normalized_topic).first()
    if cached_entry:
        return DetectSubjectResponse(
            subject=cached_entry.subject,
            confidence=cached_entry.confidence or "high",
            cached=True
        )

    result = llm_engine.detect_subject(request.topic)
    subject = result.get("subject", "Physics")
    confidence = result.get("confidence", "low")

    try:
        cache_row = TopicSubjectCache(
            topic=request.topic.strip(),
            normalized_topic=normalized_topic,
            subject=subject,
            confidence=confidence,
        )
        db.add(cache_row)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"TopicSubjectCache insert failed: {e}")

    return DetectSubjectResponse(
        subject=subject,
        confidence=confidence,
        cached=False
    )


@app.get("/api/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get current rate limit status."""
    is_allowed, remaining, reset_hours, user_limit = check_rate_limit(current_user, db)
    
    return RateLimitInfo(
        limit=user_limit,
        remaining=remaining,
        reset_hours=round(reset_hours, 2),
        used=user_limit - remaining
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
    is_allowed, remaining, reset_hours, user_limit = check_rate_limit(current_user, db)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You can generate {user_limit} PDFs per month. Limit resets on the 1st of next month."
        )
    
    try:
        # Calculate question split
        if request.num_mcqs is not None and request.num_numerical is not None:
            # Use user provided split
            mcq_count = request.num_mcqs
            numerical_count = request.num_numerical
            
            # Validate total matches
            if mcq_count + numerical_count != request.total_questions:
                # If mismatch, prioritize user split and update total (though total is used for filename)
                # Or just error? Let's be flexible and trust the split, but maybe warn?
                # Actually, let's just use the split values.
                pass
        else:
            # Default split logic
            # NEET is MCQ-only (no numerical questions)
            if request.level == "NEET":
                mcq_count = request.total_questions
                numerical_count = 0
            else:
                # 80% MCQ, 20% Numerical for JEE and others
                mcq_count = int(request.total_questions * 0.8)
                numerical_count = request.total_questions - mcq_count
                
                # Ensure at least 1 of each type for non-NEET
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
            level=request.level,
            difficulty=request.difficulty,
            # Pass extended params for GATE/JEE Advanced/Boards
            gate_paper=request.gate_paper,
            num_msq=request.num_msq,
            num_nat=request.num_nat,
            num_ga=request.num_ga,
            cbse_vsa=request.cbse_vsa,
            cbse_sa=request.cbse_sa,
            cbse_la=request.cbse_la,
            cbse_case=request.cbse_case
        )
        
        if not llm_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=llm_result.get("error", "Failed to generate questions")
            )
        
        
        # Generate filename: Top{N}_{Topic}_{Level}_{Difficulty}.pdf
        # Use actual generated count, not request.total_questions
        actual_total = mcq_count + numerical_count
        safe_topic = request.topic.replace("&", "and").replace("/", "-").replace("\\", "-")
        safe_topic = safe_topic.replace(" ", "_")
        safe_level = request.level.replace(" ", "_")
        safe_difficulty = request.difficulty
        filename = f"Top{actual_total}_{safe_topic}_{safe_level}_{safe_difficulty}"
        
        # Generate PDF
        llm_result["level"] = request.level  # Pass level to PDF template
        llm_result["difficulty"] = request.difficulty  # Pass difficulty to PDF template
        pdf_path = pdf_engine.generate_pdf(llm_result, filename)
        
        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF. Please check if pdflatex is installed."
            )
        
        # Record this generation for rate limiting
        record_generation(current_user, request, os.path.basename(pdf_path), db)
        
        # Upload to R2 and create SharedPDF record
        pdf_url = None
        shared_pdf_id = None
        if r2_storage.is_configured():
            try:
                object_key = r2_storage.get_object_key(current_user.id, os.path.basename(pdf_path))
                pdf_url = r2_storage.upload_pdf(pdf_path, object_key)
                if pdf_url:
                    # Create SharedPDF record (default: private)
                    shared_pdf = SharedPDF(
                        user_id=current_user.id,
                        pdf_url=pdf_url,
                        pdf_filename=os.path.basename(pdf_path),
                        subject=request.subject,
                        topic=request.topic,
                        level=request.level,
                        difficulty=request.difficulty,
                        question_count=mcq_count + numerical_count,
                        has_solutions=False,
                        visibility="private"
                    )
                    db.add(shared_pdf)
                    db.commit()
                    shared_pdf_id = shared_pdf.id
                    print(f"PDF uploaded to R2: {pdf_url}, SharedPDF ID: {shared_pdf_id}")
            except Exception as e:
                print(f"Warning: Failed to upload to R2: {e}")
        
        # Get updated rate limit info
        _, new_remaining, new_reset_hours, _ = check_rate_limit(current_user, db)
        
        # Read PDF file and encode as base64 for immediate download
        pdf_base64_str = None
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_base64_str = base64.b64encode(pdf_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Warning: Could not encode PDF to base64: {e}")
        
        return GenerateResponse(
            success=True,
            message="Test paper generated successfully",
            pdf_filename=os.path.basename(pdf_path),
            pdf_base64=pdf_base64_str,
            shared_pdf_id=shared_pdf_id,
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


class GenerateVerifiedResponse(BaseModel):
    """Response for verified generation endpoint."""
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    pdf_base64: Optional[str] = None  # Base64-encoded PDF for immediate download
    shared_pdf_id: Optional[str] = None  # ID for sharing/posting
    total_mcq: Optional[int] = None
    total_numerical: Optional[int] = None
    verification_stats: Optional[Dict] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset_hours: Optional[float] = None


@app.post("/api/generate-verified", response_model=GenerateVerifiedResponse)
async def generate_test_verified(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    TRIAL ENDPOINT: Generate test with numerical answer verification.
    Verifies each numerical question by re-solving it.
    """
    try:
        # Check rate limit
        is_allowed, remaining, reset_hours, total_limit = check_rate_limit(current_user, db)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. You have used all {total_limit} generations this month. Limit resets on the 1st of next month."
            )
        
        # Determine question split
        if request.num_mcqs is not None and request.num_numerical is not None:
            mcq_count = request.num_mcqs
            numerical_count = request.num_numerical
        else:
            if request.level == "NEET":
                mcq_count = request.total_questions
                numerical_count = 0
            else:
                mcq_count = int(request.total_questions * 0.8)
                numerical_count = request.total_questions - mcq_count
                if mcq_count < 1:
                    mcq_count = 1
                if numerical_count < 1:
                    numerical_count = 1
                    mcq_count = request.total_questions - 1
        
        # Generate questions WITH VERIFICATION
        llm_result = await llm_engine.generate_questions_with_verification_async(
            subject=request.subject,
            topic=request.topic,
            mcq_count=mcq_count,
            numerical_count=numerical_count,
            level=request.level,
            difficulty=request.difficulty,
            include_solutions=request.include_solutions,
            # Pass extended params
            gate_paper=request.gate_paper,
            num_msq=request.num_msq,
            num_nat=request.num_nat,
            num_ga=request.num_ga,
            cbse_vsa=request.cbse_vsa,
            cbse_sa=request.cbse_sa,
            cbse_la=request.cbse_la,
            cbse_case=request.cbse_case
        )
        
        if not llm_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=llm_result.get("error", "Failed to generate questions")
            )
        
        # Generate filename - use actual generated count
        actual_total = mcq_count + numerical_count
        safe_topic = request.topic.replace("&", "and").replace("/", "-").replace("\\", "-")
        safe_topic = safe_topic.replace(" ", "_")
        safe_level = request.level.replace(" ", "_")
        safe_difficulty = request.difficulty
        solutions_suffix = "_with_solutions" if request.include_solutions else ""
        filename = f"Top{actual_total}_{safe_topic}_{safe_level}_{safe_difficulty}{solutions_suffix}"
        
        # Generate PDF
        llm_result["level"] = request.level
        llm_result["difficulty"] = request.difficulty
        llm_result["include_solutions"] = request.include_solutions
        
        # Debug logging
        print(f"DEBUG: include_solutions = {request.include_solutions}")
        print(f"DEBUG: llm_result has include_solutions = {llm_result.get('include_solutions')}")
        questions = llm_result.get("questions", [])
        solutions_count = sum(1 for q in questions if q.get("solution"))
        print(f"DEBUG: {solutions_count}/{len(questions)} questions have solutions")
        
        pdf_path = pdf_engine.generate_pdf(llm_result, filename)
        
        if not pdf_path:
            raise HTTPException(status_code=500, detail="PDF generation failed")
        
        # Record generation
        record_generation(current_user, request, os.path.basename(pdf_path), db)
        
        # Upload to R2 in BACKGROUND (non-blocking) - don't wait for it
        # This allows PDF to return immediately to user
        shared_pdf_id = None
        if r2_storage.is_configured():
            # Create placeholder SharedPDF record (will be updated when upload completes)
            try:
                shared_pdf = SharedPDF(
                    user_id=current_user.id,
                    pdf_url="pending",  # Will be updated by background task
                    pdf_filename=os.path.basename(pdf_path),
                    subject=request.subject,
                    topic=request.topic,
                    level=request.level,
                    difficulty=request.difficulty,
                    question_count=mcq_count + numerical_count,
                    has_solutions=request.include_solutions,
                    visibility="private"
                )
                db.add(shared_pdf)
                db.commit()
                shared_pdf_id = shared_pdf.id
                
                # Schedule background upload (non-blocking)
                import asyncio
                
                async def upload_to_r2_background():
                    try:
                        object_key = r2_storage.get_object_key(current_user.id, os.path.basename(pdf_path))
                        pdf_url = await asyncio.to_thread(r2_storage.upload_pdf, pdf_path, object_key)
                        if pdf_url:
                            # Update the SharedPDF record with the actual URL
                            from database import SessionLocal
                            db_session = SessionLocal()
                            try:
                                shared = db_session.query(SharedPDF).filter(SharedPDF.id == shared_pdf_id).first()
                                if shared:
                                    shared.pdf_url = pdf_url
                                    db_session.commit()
                                    print(f"✓ Background R2 upload complete: {pdf_url}")
                            finally:
                                db_session.close()
                    except Exception as e:
                        print(f"✗ Background R2 upload failed: {e}")
                
                # Fire and forget - don't await
                asyncio.create_task(upload_to_r2_background())
                print("R2 upload scheduled in background")
            except Exception as e:
                print(f"Warning: Failed to schedule R2 upload: {e}")
        
        # Get updated rate limit info
        _, new_remaining, new_reset_hours, _ = check_rate_limit(current_user, db)
        
        # Read PDF file and encode as base64 for immediate download
        pdf_base64_str = None
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_base64_str = base64.b64encode(pdf_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Warning: Could not encode PDF to base64: {e}")
        
        return GenerateVerifiedResponse(
            success=True,
            message="Test paper generated with verified answers",
            pdf_filename=os.path.basename(pdf_path),
            pdf_base64=pdf_base64_str,
            shared_pdf_id=shared_pdf_id,
            total_mcq=mcq_count,
            total_numerical=numerical_count,
            verification_stats=llm_result.get("verification_stats"),
            rate_limit_remaining=new_remaining,
            rate_limit_reset_hours=round(new_reset_hours, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/apply-promo", response_model=ApplyPromoResponse)
async def apply_promo_code(
    request: ApplyPromoRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Apply a promo code to get bonus generations.
    """
    # Find the promo code
    promo = db.query(PromoCode).filter(
        PromoCode.code == request.code,
        PromoCode.is_active == True
    ).first()
    
    if not promo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid promo code"
        )
    
    # Check if max uses reached
    if promo.current_uses >= promo.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This promo code has expired (max uses reached)"
        )
    
    # Check if promo code has expired
    if promo.expires_at and promo.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This promo code has expired"
        )
    
    # Check if user already used this promo code
    existing_usage = db.query(PromoCodeUsage).filter(
        PromoCodeUsage.user_id == current_user.id,
        PromoCodeUsage.promo_code_id == promo.id
    ).first()
    
    if existing_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already used this promo code"
        )
    
    # Apply the promo code
    # Apply the promo code
    # 1. Add bonus to user
    if promo.is_monthly_only:
        current_user.monthly_bonus_limit = (current_user.monthly_bonus_limit or 0) + promo.bonus_limit
        current_user.last_bonus_month = datetime.now(timezone.utc).strftime("%Y-%m")
    else:
        current_user.bonus_limit = (current_user.bonus_limit or 0) + promo.bonus_limit
    
    # 2. Record usage
    usage = PromoCodeUsage(
        user_id=current_user.id,
        promo_code_id=promo.id
    )
    db.add(usage)
    
    # 3. Increment promo code usage count
    promo.current_uses += 1
    
    db.commit()
    
    # Calculate new total limit
    new_total_limit = RATE_LIMIT_COUNT + (current_user.bonus_limit or 0) + (current_user.monthly_bonus_limit or 0)
    
    return ApplyPromoResponse(
        success=True,
        message=f"Promo code applied! You now have {new_total_limit} generations.",
        new_limit=new_total_limit,
        bonus_added=promo.bonus_limit
    )



@app.post("/api/log-error")
async def log_system_error(
    request: ErrorLogRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a system error reported by the frontend.
    Accepts anonymous reports (if login fails).
    """
    try:
        # If user is authenticated, use their ID
        user_id = str(current_user.id) if current_user else None
        
        # Create log entry
        error_log = SystemErrorLog(
            error_type=request.error_type,
            error_details=request.error_details,
            user_id=user_id,
            user_email=request.user_email or (current_user.email if current_user else None),
            metadata_info=request.metadata_info
        )
        
        db.add(error_log)
        db.commit()
        
        return {"success": True, "message": "Error logged"}
        
    except Exception as e:
        print(f"Failed to log error: {e}")
        # Don't throw error to client, just fail silently
        return {"success": False, "message": "Failed to log error"}


@app.post("/api/admin/seed-promo")
async def seed_promo_code(
    admin_key: str,
    db: Session = Depends(get_db)
):
    """Seed promo codes and reset usage (Admin only)."""
    if admin_key != os.getenv("ADMIN_KEY", "admin123"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    results = []

    # 1. Create/Update Promo Code MENTORSMANTRA6
    code = "MENTORSMANTRA6"
    promo = db.query(PromoCode).filter(PromoCode.code == code).first()
    if not promo:
        promo = PromoCode(
            code=code,
            bonus_limit=6,
            max_uses=5,
            is_monthly_only=True,
            is_active=True
        )
        db.add(promo)
        results.append(f"Created {code}")
    else:
        promo.bonus_limit = 6
        promo.max_uses = 5
        promo.is_monthly_only = True
        promo.is_active = True
        results.append(f"Updated {code}")
    
    # 3. Reset Usage for Current Month
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    deleted = db.query(PDFGeneration).filter(
        PDFGeneration.created_at >= start_of_month
    ).delete(synchronize_session=False)
    
    results.append(f"Deleted {deleted} records from current month")
    
    db.commit()
    
    return {"message": "Admin tasks completed", "details": results}


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


# ============== SSE ENDPOINTS FOR RESILIENT GENERATION ==============

class SSEStartResponse(BaseModel):
    """Response for SSE start endpoint."""
    job_id: str
    message: str


@app.post("/api/generate-sse/start", response_model=SSEStartResponse)
async def start_sse_generation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Start a PDF generation job and return job_id for SSE streaming.
    The actual generation happens in the background.
    """
    # Check rate limit
    is_allowed, remaining, reset_hours, total_limit = check_rate_limit(current_user, db)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You have used all {total_limit} generations this month."
        )
    
    # Create job
    job = job_store.create_job(str(current_user.id))
    
    # Start generation in background
    background_tasks.add_task(
        run_generation_job,
        job.job_id,
        request,
        current_user,
        db
    )
    
    return SSEStartResponse(
        job_id=job.job_id,
        message="Generation started. Connect to SSE stream for progress."
    )


async def run_generation_job(
    job_id: str,
    request: GenerateRequest,
    user: User,
    db: Session
):
    """Background task to run PDF generation with progress updates."""
    import asyncio
    
    try:
        # Update: Analyzing
        job_store.update_job(job_id, JobStatus.ANALYZING, 5, "Analyzing topic and difficulty...")
        
        # DEBUG: Log incoming request values
        print(f"[DEBUG] Request received: level={request.level}, total_questions={request.total_questions}")
        print(f"[DEBUG] num_mcqs={request.num_mcqs}, num_numerical={request.num_numerical}")
        print(f"[DEBUG] GATE params: gate_paper={request.gate_paper}, num_ga={request.num_ga}, num_msq={request.num_msq}, num_nat={request.num_nat}")
        
        # Determine question split
        # GATE has special handling - all questions go through mcq_count for the prompt
        if request.level == "GATE":
            # For GATE, combine all question types into a single count
            num_ga = request.num_ga or 0
            num_mcq = request.num_mcqs or 0
            num_msq = request.num_msq or 0
            num_nat = request.num_nat or 0
            total_gate = num_ga + num_mcq + num_msq + num_nat
            
            # Pass total as mcq_count, the prompt will handle the distribution
            mcq_count = total_gate
            numerical_count = 0  # NATs are handled inside the prompt
            print(f"[DEBUG] GATE: Using total count mcq_count={mcq_count}, numerical_count={numerical_count}")
        elif request.num_mcqs is not None and request.num_numerical is not None:
            mcq_count = request.num_mcqs
            numerical_count = request.num_numerical
            print(f"[DEBUG] Using explicit counts: mcq_count={mcq_count}, numerical_count={numerical_count}")
        else:
            if request.level == "NEET":
                mcq_count = request.total_questions
                numerical_count = 0
            else:
                mcq_count = int(request.total_questions * 0.8)
                numerical_count = request.total_questions - mcq_count
                if mcq_count < 1:
                    mcq_count = 1
                if numerical_count < 1:
                    numerical_count = 1
                    mcq_count = request.total_questions - 1
            print(f"[DEBUG] Using fallback split: mcq_count={mcq_count}, numerical_count={numerical_count}")
        
        # Update: Generating MCQs
        job_store.update_job(job_id, JobStatus.GENERATING_MCQS, 15, f"Generating {mcq_count} MCQ questions...")
        
        # Fresh Questions: Fetch history if enabled
        past_questions = []
        fresh_questions_enabled = getattr(user, 'fresh_questions_enabled', True)
        if fresh_questions_enabled:
            try:
                past_questions = get_user_question_history(
                    db=db,
                    user_id=user.id,
                    topic=request.topic,
                    level=request.level,
                    limit=50
                )
                if past_questions:
                    print(f"Found {len(past_questions)} past questions for {request.topic}/{request.level}")
            except Exception as e:
                print(f"Warning: Could not fetch question history: {e}")
                past_questions = []
        
        # Generate questions WITH VERIFICATION
        llm_result = await llm_engine.generate_questions_with_verification_async(
            subject=request.subject,
            topic=request.topic,
            mcq_count=mcq_count,
            numerical_count=numerical_count,
            level=request.level,
            difficulty=request.difficulty,
            include_solutions=request.include_solutions,
            # GATE Parameters
            gate_paper=request.gate_paper,
            num_msq=request.num_msq,
            num_nat=request.num_nat,
            num_ga=request.num_ga,
            # Fresh Questions: Pass past questions to avoid repetition
            past_questions=past_questions if fresh_questions_enabled else None,
            # Boards Parameters
            cbse_vsa=request.cbse_vsa,
            cbse_sa=request.cbse_sa,
            cbse_la=request.cbse_la,
            cbse_case=request.cbse_case
        )

        
        if not llm_result.get("success"):
            job_store.update_job(
                job_id,
                JobStatus.FAILED,
                0,
                "Failed to generate questions",
                error=llm_result.get("error", "Unknown error")
            )
            return
        
        # Update: Verifying
        job_store.update_job(job_id, JobStatus.VERIFYING, 60, "Verifying answers...")
        
        # Fresh Questions: Save generated questions to history
        if fresh_questions_enabled and llm_result.get("questions"):
            try:
                question_texts = [q.get("question", "") for q in llm_result.get("questions", [])]
                save_question_history(
                    db=db,
                    user_id=user.id,
                    topic=request.topic,
                    level=request.level,
                    questions=question_texts
                )
            except Exception as e:
                print(f"Warning: Could not save question history: {e}")
        
        # Generate filename
        actual_total = mcq_count + numerical_count
        safe_topic = request.topic.replace("&", "and").replace("/", "-").replace("\\", "-")
        safe_topic = safe_topic.replace(" ", "_")
        safe_level = request.level.replace(" ", "_")
        safe_difficulty = request.difficulty
        solutions_suffix = "_with_solutions" if request.include_solutions else ""
        filename = f"Top{actual_total}_{safe_topic}_{safe_level}_{safe_difficulty}{solutions_suffix}"
        
        # Update: Compiling PDF
        job_store.update_job(job_id, JobStatus.COMPILING_PDF, 75, "Compiling PDF document...")
        
        # Generate PDF
        llm_result["level"] = request.level
        llm_result["difficulty"] = request.difficulty
        llm_result["include_solutions"] = request.include_solutions
        
        pdf_path = pdf_engine.generate_pdf(llm_result, filename)
        
        if not pdf_path:
            job_store.update_job(
                job_id,
                JobStatus.FAILED,
                0,
                "PDF generation failed",
                error="PDF engine returned no path"
            )
            return
        
        # Record generation
        record_generation(user, request, os.path.basename(pdf_path), db)
        print(f"[SSE Job {job_id}] TRACE: After record_generation")
        
        # Read PDF and encode
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
        print(f"[SSE Job {job_id}] TRACE: After PDF encoding, size={len(pdf_base64)}")
        
        # Count questions
        questions = llm_result.get("questions", [])
        total_mcq = sum(1 for q in questions if q.get("type") in ["mcq", "mcq_multi"])
        total_numerical = sum(1 for q in questions if q.get("type") == "numerical")
        
        # Get updated rate limit
        _, new_remaining, new_reset_hours, _ = check_rate_limit(user, db)
        print(f"[SSE Job {job_id}] TRACE: Before R2 section, rate_limit={new_remaining}")
        
        # Create SharedPDF record FIRST (so Post button shows), then attempt GCS upload in background
        shared_pdf_id = None
        try:
            from database import SessionLocal
            db_session = SessionLocal()
            try:
                # Create SharedPDF with pending URL immediately
                shared_pdf = SharedPDF(
                    user_id=user.id,
                    pdf_url="pending",  # Will be updated after GCS upload
                    pdf_filename=os.path.basename(pdf_path),
                    subject=request.subject,
                    topic=request.topic,
                    level=request.level,
                    difficulty=request.difficulty,
                    question_count=mcq_count + numerical_count,
                    has_solutions=request.include_solutions,
                    visibility="private"
                )
                db_session.add(shared_pdf)
                db_session.commit()
                shared_pdf_id = shared_pdf.id
                print(f"✓ SharedPDF created: {shared_pdf_id}")
            finally:
                db_session.close()
        except Exception as e:
            print(f"✗ Failed to create SharedPDF: {e}")
        
        # Attempt GCS upload in background (non-blocking) to update pdf_url later
        if gcs_storage.is_configured() and shared_pdf_id:
            job_store.update_job(job_id, JobStatus.UPLOADING, 90, "Uploading to cloud storage...")
            try:
                object_key = gcs_storage.get_object_key(str(user.id), os.path.basename(pdf_path))
                print(f"[SSE Job {job_id}] Attempting GCS upload: {object_key}")
                pdf_url = gcs_storage.upload_pdf(pdf_path, object_key)
                
                if pdf_url:
                    # Update SharedPDF with actual GCS URL
                    db_session = SessionLocal()
                    try:
                        shared = db_session.query(SharedPDF).filter(SharedPDF.id == shared_pdf_id).first()
                        if shared:
                            shared.pdf_url = pdf_url
                            db_session.commit()
                            print(f"✓ GCS upload complete: {pdf_url}")
                    finally:
                        db_session.close()
                else:
                    print(f"[SSE Job {job_id}] GCS upload returned None")
            except Exception as e:
                print(f"✗ GCS upload failed: {e}")
        
        # Update: Done
        job_store.update_job(
            job_id,
            JobStatus.DONE,
            100,
            "PDF ready for download!",
            result={
                "success": True,
                "message": f"Generated {len(questions)} questions successfully!",
                "pdf_filename": os.path.basename(pdf_path),
                "pdf_base64": pdf_base64,
                "shared_pdf_id": shared_pdf_id,
                "total_mcq": total_mcq,
                "total_numerical": total_numerical,
                "rate_limit_remaining": new_remaining,
                "rate_limit_reset_hours": new_reset_hours
            }
        )
        
    except Exception as e:
        print(f"[SSE Job {job_id}] Error: {str(e)}")
        
        # Auto-log generation failure
        try:
            # Use local import to avoid circular dependency issues if any
            from database import SessionLocal
            from models import SystemErrorLog
            err_db = SessionLocal()
            try:
                err_log = SystemErrorLog(
                    error_type="GENERATION_FAILURE",
                    error_details=f"Job {job_id} failed: {str(e)}",
                    user_id=str(user.id),
                    user_email=user.email,
                    metadata_info=json.dumps({"level": request.level, "subject": request.subject, "topic": request.topic})
                )
                err_db.add(err_log)
                err_db.commit()
                print(f"[SystemLog] Logged generation failure for {job_id}")
            except Exception as log_err:
                print(f"Failed to auto-log error: {log_err}")
            finally:
                err_db.close()
        except Exception:
            pass
            
        job_store.update_job(
            job_id,
            JobStatus.FAILED,
            0,
            "An error occurred",
            error=str(e)
        )


@app.get("/api/generate-sse/{job_id}/stream")
async def stream_job_progress(
    job_id: str, 
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    SSE endpoint to stream job progress updates.
    Client should connect here after getting job_id from /start.
    Note: Uses token query param since EventSource doesn't support headers.
    """
    import asyncio
    from auth import decode_token
    
    # Authenticate via query param token
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
    
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns this job
    if job.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    
    async def event_generator():
        # Subscribe to job updates
        queue = job_store.subscribe(job_id)
        
        try:
            # Send current state first
            current_job = job_store.get_job(job_id)
            if current_job:
                yield f"data: {json.dumps(current_job.to_dict())}\n\n"
            
            # If already done/failed, close
            if current_job and current_job.status in [JobStatus.DONE, JobStatus.FAILED]:
                return
            
            # Wait for updates
            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(update)}\n\n"
                    
                    # Check if done
                    if update.get("status") in ["done", "failed"]:
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    
                    # Check if job still exists
                    current_job = job_store.get_job(job_id)
                    if not current_job or current_job.status in [JobStatus.DONE, JobStatus.FAILED]:
                        break
        finally:
            job_store.unsubscribe(job_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/generate-sse/{job_id}/status")
async def get_job_status(job_id: str, current_user: User = Depends(get_current_user_required)):
    """
    Poll endpoint to get current job status.
    Useful for reconnection after network drops.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    
    # Verify user owns this job
    if job.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    
    return job.to_dict()


# ============== END SSE ENDPOINTS ==============


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
