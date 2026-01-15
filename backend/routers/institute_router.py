"""
Institute Router - Authentication and API endpoints for institute users.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import InstituteUser, InstituteRefreshToken, InstituteGeneration
from auth import (
    get_password_hash, verify_password, create_access_token, decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from services.llm_engine import llm_engine
from services.pdf_engine import pdf_engine

router = APIRouter(prefix="/api/institute", tags=["institute"])


# ============ Pydantic Models ============

class InstituteLoginRequest(BaseModel):
    email: str
    password: str


class InstituteLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class InstituteProfileUpdate(BaseModel):
    institute_name: Optional[str] = None
    contact_number: Optional[str] = None
    institute_email: Optional[str] = None


class InstituteProfileResponse(BaseModel):
    id: str
    email: str
    institute_name: Optional[str]
    contact_number: Optional[str]
    institute_email: Optional[str]


class ChapterClassification(BaseModel):
    chapter: str
    subject: str


class InstituteGenerateRequest(BaseModel):
    chapters: List[str] = Field(..., description="List of chapter names")
    exam_type: str = Field(..., description="Mains, NEET, or Advanced")
    difficulty: str = Field(..., description="Easy, Medium, or Hard")
    physics_count: Optional[int] = None
    chemistry_count: Optional[int] = None
    maths_count: Optional[int] = None
    zoology_count: Optional[int] = None  # For NEET
    botany_count: Optional[int] = None   # For NEET


class InstituteGenerateResponse(BaseModel):
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    chapters_classified: List[ChapterClassification]
    verification_stats: Optional[dict] = None


class CreateInstituteRequest(BaseModel):
    email: str
    password: str


# ============ Auth Helpers ============

def create_institute_refresh_token(user_id: str, db: Session) -> tuple:
    """Create refresh token for institute user."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    token = InstituteRefreshToken(
        institute_user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(token)
    db.commit()
    db.refresh(token)
    
    return token.token, expires_at


async def get_current_institute_user(
    token: str = None,
    db: Session = Depends(get_db)
) -> Optional[InstituteUser]:
    """Get current institute user from JWT token."""
    if not token:
        return None
    
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != "access" or payload.get("user_type") != "institute":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    return db.query(InstituteUser).filter(InstituteUser.id == user_id).first()


async def get_institute_user_required(
    authorization: str = None,
    db: Session = Depends(get_db)
) -> InstituteUser:
    """Get institute user, raise 401 if not authenticated."""
    from fastapi import Header
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # This will be called differently - we need to extract token from header
    return credentials_exception  # Placeholder


# ============ Dependency for Auth ============

from fastapi.security import OAuth2PasswordBearer

institute_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/institute/login", auto_error=False)


async def get_institute_user(
    token: Optional[str] = Depends(institute_oauth2_scheme),
    db: Session = Depends(get_db)
) -> InstituteUser:
    """Get current authenticated institute user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    if payload.get("type") != "access" or payload.get("user_type") != "institute":
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    user = db.query(InstituteUser).filter(InstituteUser.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    
    return user


# ============ Endpoints ============

@router.post("/login", response_model=InstituteLoginResponse)
async def institute_login(request: InstituteLoginRequest, db: Session = Depends(get_db)):
    """Login for institute users."""
    user = db.query(InstituteUser).filter(InstituteUser.email == request.email).first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create tokens with user_type
    access_token = create_access_token(
        data={"sub": user.id, "user_type": "institute"}
    )
    refresh_token, _ = create_institute_refresh_token(user.id, db)
    
    return InstituteLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "institute_name": user.institute_name,
            "contact_number": user.contact_number,
            "institute_email": user.institute_email
        }
    )


class InstituteRefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_institute_token(request: InstituteRefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token for institute users."""
    # Find the refresh token
    token_record = db.query(InstituteRefreshToken).filter(
        InstituteRefreshToken.token == request.refresh_token,
        InstituteRefreshToken.is_revoked == False,
        InstituteRefreshToken.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get the user
    user = db.query(InstituteUser).filter(InstituteUser.id == token_record.institute_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token = create_access_token(
        data={"sub": user.id, "user_type": "institute"}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/profile", response_model=InstituteProfileResponse)
async def get_profile(current_user: InstituteUser = Depends(get_institute_user)):
    """Get institute profile."""
    return InstituteProfileResponse(
        id=current_user.id,
        email=current_user.email,
        institute_name=current_user.institute_name,
        contact_number=current_user.contact_number,
        institute_email=current_user.institute_email
    )


@router.put("/profile", response_model=InstituteProfileResponse)
async def update_profile(
    profile: InstituteProfileUpdate,
    current_user: InstituteUser = Depends(get_institute_user),
    db: Session = Depends(get_db)
):
    """Update institute profile."""
    if profile.institute_name is not None:
        current_user.institute_name = profile.institute_name
    if profile.contact_number is not None:
        current_user.contact_number = profile.contact_number
    if profile.institute_email is not None:
        current_user.institute_email = profile.institute_email
    
    db.commit()
    db.refresh(current_user)
    
    return InstituteProfileResponse(
        id=current_user.id,
        email=current_user.email,
        institute_name=current_user.institute_name,
        contact_number=current_user.contact_number,
        institute_email=current_user.institute_email
    )


class DetectSubjectsRequest(BaseModel):
    chapters: List[str]


class DetectSubjectsResponse(BaseModel):
    classifications: List[ChapterClassification]


@router.post("/detect-subjects", response_model=DetectSubjectsResponse)
async def detect_subjects(
    request: DetectSubjectsRequest,
    current_user: InstituteUser = Depends(get_institute_user)
):
    """Detect subjects for each chapter using AI."""
    classifications = []
    
    for chapter in request.chapters:
        if not chapter.strip():
            continue
        result = llm_engine.detect_subject(chapter.strip())
        subject = result.get("subject", "Physics")
        classifications.append(ChapterClassification(chapter=chapter.strip(), subject=subject))
    
    return DetectSubjectsResponse(classifications=classifications)


@router.post("/generate", response_model=InstituteGenerateResponse)
async def generate_institute_test(
    request: InstituteGenerateRequest,
    current_user: InstituteUser = Depends(get_institute_user),
    db: Session = Depends(get_db)
):
    """Generate test paper for institute with multiple chapters and subjects."""
    
    # Define exam limits
    EXAM_LIMITS = {
        "Mains": {"Physics": 25, "Chemistry": 25, "Maths": 25},
        "NEET": {"Physics": 45, "Chemistry": 45, "Zoology": 45, "Botany": 45},
        "Advanced": {"Physics": 18, "Chemistry": 18, "Maths": 18}
    }
    
    if request.exam_type not in EXAM_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid exam type: {request.exam_type}")
    
    limits = EXAM_LIMITS[request.exam_type]
    
    # Step 1: Classify each chapter by subject
    chapters_classified = []
    chapters_by_subject = {"Physics": [], "Chemistry": [], "Maths": [], "Zoology": [], "Botany": []}
    
    for chapter in request.chapters:
        if not chapter.strip():
            continue
        result = llm_engine.detect_subject(chapter.strip())
        subject = result.get("subject", "Physics")
        chapters_classified.append(ChapterClassification(chapter=chapter.strip(), subject=subject))
        if subject in chapters_by_subject:
            chapters_by_subject[subject].append(chapter.strip())
    
    # Step 2: Determine question counts
    if request.exam_type == "NEET":
        phy_count = min(request.physics_count or limits["Physics"], limits["Physics"])
        chem_count = min(request.chemistry_count or limits["Chemistry"], limits["Chemistry"])
        zoo_count = min(request.zoology_count or limits["Zoology"], limits["Zoology"])
        bot_count = min(request.botany_count or limits["Botany"], limits["Botany"])
        maths_count = 0
    else:
        phy_count = min(request.physics_count or limits["Physics"], limits["Physics"])
        chem_count = min(request.chemistry_count or limits["Chemistry"], limits["Chemistry"])
        maths_count = min(request.maths_count or limits["Maths"], limits["Maths"])
        zoo_count = 0
        bot_count = 0
    
    # Step 3: Generate questions for each subject
    all_questions = []
    verification_stats = {"total_numerical": 0, "verified": 0, "corrected": 0}
    
    async def generate_for_subject(subject, chapters, count, exam_type, difficulty):
        if count == 0 or not chapters:
            return []
        
        topic = ", ".join(chapters)
        # 80% MCQ, 20% Numerical (NEET is all MCQ)
        if exam_type == "NEET":
            mcq_count = count
            num_count = 0
        else:
            mcq_count = int(count * 0.8)
            num_count = count - mcq_count
        
        result = await llm_engine.generate_questions_with_verification_async(
            subject=subject,
            topic=topic,
            mcq_count=mcq_count,
            numerical_count=num_count,
            level=exam_type,
            difficulty=difficulty
        )
        
        if result.get("success"):
            questions = result.get("questions", [])
            # Add subject label to each question
            for q in questions:
                q["subject"] = subject
            
            # Accumulate verification stats
            stats = result.get("verification_stats", {})
            verification_stats["total_numerical"] += stats.get("total_numerical", 0)
            verification_stats["verified"] += stats.get("verified", 0)
            verification_stats["corrected"] += stats.get("corrected", 0)
            
            return questions
        return []
    
    # Generate for each subject
    import asyncio
    
    tasks = []
    if phy_count > 0 and chapters_by_subject["Physics"]:
        tasks.append(generate_for_subject("Physics", chapters_by_subject["Physics"], phy_count, request.exam_type, request.difficulty))
    if chem_count > 0 and chapters_by_subject["Chemistry"]:
        tasks.append(generate_for_subject("Chemistry", chapters_by_subject["Chemistry"], chem_count, request.exam_type, request.difficulty))
    if maths_count > 0 and chapters_by_subject["Maths"]:
        tasks.append(generate_for_subject("Maths", chapters_by_subject["Maths"], maths_count, request.exam_type, request.difficulty))
    if zoo_count > 0 and chapters_by_subject["Zoology"]:
        tasks.append(generate_for_subject("Zoology", chapters_by_subject["Zoology"], zoo_count, request.exam_type, request.difficulty))
    if bot_count > 0 and chapters_by_subject["Botany"]:
        tasks.append(generate_for_subject("Botany", chapters_by_subject["Botany"], bot_count, request.exam_type, request.difficulty))
    
    if not tasks:
        raise HTTPException(status_code=400, detail="No valid chapters to generate questions from")
    
    results = await asyncio.gather(*tasks)
    for questions in results:
        all_questions.extend(questions)
    
    if not all_questions:
        raise HTTPException(status_code=500, detail="Failed to generate questions")
    
    # Step 4: Generate PDF with institute branding
    topic_str = ", ".join(request.chapters[:3])  # First 3 chapters for filename
    if len(request.chapters) > 3:
        topic_str += f" +{len(request.chapters) - 3} more"
    
    safe_topic = topic_str.replace("&", "and").replace("/", "-").replace("\\", "-").replace(" ", "_")[:50]
    filename = f"Institute_{request.exam_type}_{request.difficulty}_{safe_topic}"
    
    # Prepare PDF data
    pdf_data = {
        "subject": "Multi-Subject",
        "topic": ", ".join(request.chapters),
        "level": request.exam_type,
        "difficulty": request.difficulty,
        "questions": all_questions,
        # Institute branding
        "institute_name": current_user.institute_name or "",
        "institute_contact": current_user.contact_number or "",
        "institute_email": current_user.institute_email or "",
        "is_institute": True
    }
    
    pdf_path = pdf_engine.generate_pdf(pdf_data, filename)
    
    if not pdf_path:
        raise HTTPException(status_code=500, detail="PDF generation failed")
    
    # Record generation
    generation = InstituteGeneration(
        institute_user_id=current_user.id,
        chapters=json.dumps(request.chapters),
        exam_type=request.exam_type,
        difficulty=request.difficulty,
        physics_count=phy_count,
        chemistry_count=chem_count,
        maths_count=maths_count,
        biology_count=zoo_count + bot_count,
        pdf_filename=os.path.basename(pdf_path)
    )
    db.add(generation)
    db.commit()
    
    return InstituteGenerateResponse(
        success=True,
        message=f"Test paper generated with {len(all_questions)} questions",
        pdf_filename=os.path.basename(pdf_path),
        chapters_classified=chapters_classified,
        verification_stats=verification_stats
    )


# ============ Admin Endpoint ============

@router.post("/admin/create", response_model=dict)
async def create_institute_account(
    request: CreateInstituteRequest,
    admin_key: str = None,
    db: Session = Depends(get_db)
):
    """Admin endpoint to create institute accounts."""
    # Verify admin key
    expected_key = os.getenv("ADMIN_KEY", "admin123")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Check if email exists
    existing = db.query(InstituteUser).filter(InstituteUser.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = InstituteUser(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": f"Institute account created for {request.email}",
        "user_id": user.id
    }
