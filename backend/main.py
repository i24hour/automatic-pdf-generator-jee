"""
Mentors Mantra Test Generator - FastAPI Backend
Main application entry point with API endpoints.
"""

import os
import uuid
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from services.llm_engine import llm_engine
from services.pdf_engine import pdf_engine
from database import get_db, init_db
from models import User, PDFGeneration, PromoCode, PromoCodeUsage, TopicSubjectCache
from auth import get_current_user_required, get_current_user
from routers.auth_router import router as auth_router
from routers.institute_router import router as institute_router

# Load environment variables
load_dotenv()

# Rate limiting configuration
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "30"))
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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include auth router
app.include_router(auth_router)
app.include_router(institute_router)


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
    level: str = Field(default="JEE Mains", description="Exam type: Boards, JEE Mains, JEE Advanced, Olympiad, NEET")
    difficulty: str = Field(default="Medium", description="Difficulty within exam: Easy, Medium, Hard")
    num_mcqs: Optional[int] = Field(default=None, description="Number of MCQs (optional)")
    num_numerical: Optional[int] = Field(default=None, description="Number of numerical questions (optional)")


class GenerateResponse(BaseModel):
    """Response model for successful generation."""
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    pdf_base64: Optional[str] = None  # Base64-encoded PDF for immediate download
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
            detail=f"Rate limit exceeded. You can generate {user_limit} PDFs every {RATE_LIMIT_HOURS} hours. Try again in {reset_hours:.1f} hours."
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
            difficulty=request.difficulty
        )
        
        if not llm_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=llm_result.get("error", "Failed to generate questions")
            )
        
        
        # Generate filename: Top{N}_{Topic}_{Level}_{Difficulty}.pdf
        # Sanitize topic for filename (replace special chars)
        safe_topic = request.topic.replace("&", "and").replace("/", "-").replace("\\", "-")
        safe_topic = safe_topic.replace(" ", "_")
        safe_level = request.level.replace(" ", "_")
        safe_difficulty = request.difficulty
        filename = f"Top{request.total_questions}_{safe_topic}_{safe_level}_{safe_difficulty}"
        
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
                detail=f"Rate limit exceeded. You have used all {total_limit} generations this month. Resets in {reset_hours:.1f} hours."
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
            difficulty=request.difficulty
        )
        
        if not llm_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=llm_result.get("error", "Failed to generate questions")
            )
        
        # Generate filename
        safe_topic = request.topic.replace("&", "and").replace("/", "-").replace("\\", "-")
        safe_topic = safe_topic.replace(" ", "_")
        safe_level = request.level.replace(" ", "_")
        safe_difficulty = request.difficulty
        filename = f"Verified_Top{request.total_questions}_{safe_topic}_{safe_level}_{safe_difficulty}"
        
        # Generate PDF
        llm_result["level"] = request.level
        llm_result["difficulty"] = request.difficulty
        pdf_path = pdf_engine.generate_pdf(llm_result, filename)
        
        if not pdf_path:
            raise HTTPException(status_code=500, detail="PDF generation failed")
        
        # Record generation
        record_generation(current_user, request, os.path.basename(pdf_path), db)
        
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


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
