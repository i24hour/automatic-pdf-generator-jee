from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json

from database import get_db
from models import User, Test, TestLeaderboard, TestAttempt, QuestionResponse, generate_uuid
from auth import get_current_user_required, get_current_user_optional
from services.llm_engine import llm_engine

router = APIRouter(
    prefix="/api/community",
    tags=["Community Tests"]
)

# --- Schemas ---

class TestSummarySchema(BaseModel):
    id: str
    title: str
    subject: str
    topics: List[str]
    exam_type: str
    difficulty: str
    total_questions: int
    total_marks: int
    duration_minutes: int
    attempt_count: int
    creator_name: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class TestDetailSchema(TestSummarySchema):
    questions_data: Optional[List[Dict[str, Any]]] = None # Only returned if creating attempt or owner

class LeaderboardEntrySchema(BaseModel):
    rank: int
    user_name: str
    score: int
    accuracy: float
    time_taken_seconds: int
    submitted_at: datetime
    is_current_user: bool = False

class CreatePublicTestRequest(BaseModel):
    # Generation params
    subject: str
    topic: str
    total_questions: int
    level: str
    difficulty: str # legacy Easy/Medium/Hard or distribution
    duration_minutes: int
    
    # Optional: if client wants to provide questions directly
    questions_data: Optional[List[Dict[str, Any]]] = None

# --- Endpoints ---

@router.get("/tests", response_model=List[TestSummarySchema])
def search_tests(
    search: Optional[str] = None,
    subject: Optional[str] = None,
    exam_type: Optional[str] = None,
    sort_by: str = Query("newest", regex="^(newest|popular|trending)$"),
    db: Session = Depends(get_db)
):
    """Search for public community tests."""
    query = db.query(Test).filter(Test.is_public == True)
    
    if search:
        # Search by title or topics
        query = query.filter(or_(
            Test.title.ilike(f"%{search}%"),
            Test.topics_json.ilike(f"%{search}%")
        ))
    
    if subject:
        query = query.filter(Test.subject == subject)
    
    if exam_type:
        query = query.filter(Test.exam_type == exam_type)
        
    # Sorting
    if sort_by == "popular":
        query = query.order_by(desc(Test.attempt_count))
    elif sort_by == "trending":
        # Simple trending: attempts in last 7 days (simplified to just attempts for MVP)
        query = query.order_by(desc(Test.attempt_count), desc(Test.created_at))
    else: # newest
        query = query.order_by(desc(Test.created_at))
        
    tests = query.limit(50).all()
    
    # Enrich with creator name (optimize with join later)
    results = []
    for t in tests:
        topics = json.loads(t.topics_json) if t.topics_json else []
        creator_name = t.creator.name if t.creator else "Unknown"
        results.append({
            "id": t.id,
            "title": t.title,
            "subject": t.subject,
            "topics": topics,
            "exam_type": t.exam_type,
            "difficulty": t.difficulty,
            "total_questions": t.total_questions,
            "total_marks": t.total_marks,
            "duration_minutes": t.duration_minutes,
            "attempt_count": t.attempt_count,
            "creator_name": creator_name,
            "created_at": t.created_at
        })
        
    return results

@router.post("/tests/create")
async def create_public_test( # Async for LLM
    request: CreatePublicTestRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Save a generated test as a public community test."""
    
    final_questions = request.questions_data
    
    # Generate if not provided
    if not final_questions:
        # Determine MCQ/Numerical split (simple logic for now)
        # Default: 100% MCQs for simplicity unless specified
        mcq_count = request.total_questions
        numerical_count = 0
        
        # Call LLM
        result = await llm_engine.generate_with_fallback_async(
            subject=request.subject,
            topic=request.topic,
            mcq_count=mcq_count,
            numerical_count=numerical_count,
            level=request.level,
            difficulty=request.difficulty
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=f"Generation failed: {result.get('error')}")
            
        final_questions = result.get("questions", [])
    
    # Calculate metadata
    total_marks = sum(q.get("marks", 4) for q in final_questions) # Default 4 marks
    
    # Determine title relative to topic
    title = f"{request.topic} - {request.level} Practice"
    
    new_test = Test(
        title=title,
        creator_id=current_user.id,
        subject=request.subject,
        topics_json=json.dumps([request.topic]), # Single topic for now
        exam_type=request.level,
        difficulty=request.difficulty,
        total_questions=len(final_questions),
        total_marks=total_marks,
        duration_minutes=request.duration_minutes,
        questions_data=json.dumps(final_questions),
        is_public=True
    )
    
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    
    return {"id": new_test.id, "message": "Test published to community"}

@router.get("/tests/{test_id}", response_model=TestDetailSchema)
def get_test_details(
    test_id: str,
    db: Session = Depends(get_db)
):
    """Get metadata for a specific test."""
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
        
    topics = json.loads(test.topics_json) if test.topics_json else []
    creator_name = test.creator.name if test.creator else "Unknown"
    
    return {
        "id": test.id,
        "title": test.title,
        "subject": test.subject,
        "topics": topics,
        "exam_type": test.exam_type,
        "difficulty": test.difficulty,
        "total_questions": test.total_questions,
        "total_marks": test.total_marks,
        "duration_minutes": test.duration_minutes,
        "attempt_count": test.attempt_count,
        "creator_name": creator_name,
        "created_at": test.created_at,
        "questions_data": None # Don't leak questions here
    }

@router.get("/tests/{test_id}/leaderboard", response_model=List[LeaderboardEntrySchema])
def get_leaderboard(
    test_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get top 50 rankers for a test."""
    leaderboard = db.query(TestLeaderboard)\
        .filter(TestLeaderboard.test_id == test_id)\
        .order_by(desc(TestLeaderboard.score), TestLeaderboard.time_taken_seconds)\
        .limit(50)\
        .all()
        
    results = []
    for idx, entry in enumerate(leaderboard):
        user_name = entry.user.username if entry.user and entry.user.username else (entry.user.name if entry.user else "Anonymous")
        is_me = current_user and entry.user_id == current_user.id
        
        results.append({
            "rank": idx + 1,
            "user_name": user_name,
            "score": entry.score,
            "accuracy": float(entry.accuracy), # Ensure float
            "time_taken_seconds": entry.time_taken_seconds,
            "submitted_at": entry.submitted_at,
            "is_current_user": is_me
        })
        
    return results
    return results

@router.post("/tests/{test_id}/start")
def start_community_test(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Start an attempt for a community test."""
    
    # 1. Fetch Master Test
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
        
    # Check if already in progress? (Optional, skipping for now to allow retries)
    
    # 2. Create Test Attempt
    attempt = TestAttempt(
        user_id=current_user.id,
        test_id=test.id, # Link to master test
        exam_type=test.exam_type,
        total_questions=test.total_questions,
        duration_minutes=test.duration_minutes,
        topics_json=test.topics_json,
        subject_distribution_json=json.dumps({test.subject: test.total_questions}), # Simplified
        status="NOT_STARTED"
    )
    db.add(attempt)
    db.flush() # Get ID
    
    # 3. Populate Questions from Master
    questions = json.loads(test.questions_data)
    
    for idx, q_data in enumerate(questions):
        # Extract options
        options_dict = {}
        if "options" in q_data and isinstance(q_data["options"], list):
            labels = ["A", "B", "C", "D"]
            for i, opt in enumerate(q_data["options"][:4]):
                options_dict[labels[i]] = opt
        elif "options" in q_data and isinstance(q_data["options"], dict):
            options_dict = q_data["options"]
            
        # Extract correct answer
        correct_ans = q_data.get("answer", "A")
        
        # Determine specific mark if available, else default to 4/-1
        marks = q_data.get("marks", 4)
        
        response = QuestionResponse(
            test_attempt_id=attempt.id,
            question_index=idx,
            subject=test.subject, # Or q_data.get("subject")
            topic=test.title, # Or q_data.get("topic")
            difficulty=test.difficulty,
            question_type=q_data.get("type", "mcq"),
            question_text=q_data.get("question_text", q_data.get("text", "Question text missing")),
            options_json=json.dumps(options_dict),
            correct_answer=correct_ans,
            marks_correct=marks,
            marks_wrong=-1, # TODO: Configurable?
            status="NOT_VISITED",
            diagram_json=json.dumps(q_data.get("diagram_spec")) if q_data.get("diagram_spec") else None
        )
        db.add(response)
        
    # Increment attempt count on master test
    test.attempt_count += 1
    
    db.commit()
    
    return {
        "attempt_id": attempt.id,
        "message": "Test attempt started",
        "redirect_url": f"/test/{attempt.id}/instructions" # Reuse existing instructions flow
    }
