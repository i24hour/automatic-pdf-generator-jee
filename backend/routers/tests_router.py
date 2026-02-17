from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import asyncio
import uuid

from database import get_db
from models import User, Test, generate_uuid
from auth import get_current_user_required
from services.llm_engine import llm_engine

router = APIRouter(
    prefix="/api/tests",
    tags=["Tests Management"]
)

# --- Schemas ---

class SubjectInput(BaseModel):
    count: int
    difficulty: dict  # {"easy": 20, "medium": 50, "hard": 30}
    topics: List[str]

class CreateTestRequest(BaseModel):
    exam_type: str  # JEE_MAINS, NEET, CUSTOM
    subject_inputs: Dict[str, SubjectInput]
    duration_minutes: int
    visibility: str = "PRIVATE" # PRIVATE, CLASSROOM, COMMUNITY
    classroom_id: Optional[str] = None

class TestCreatedResponse(BaseModel):
    test_id: str
    message: str
    status: str

class MyTestSchema(BaseModel):
    id: str
    title: str
    subject: str
    created_at: datetime
    attempt_count: int
    visibility: str
    status: str

# --- Endpoints ---

@router.post("/create", response_model=TestCreatedResponse)
async def create_test(
    request: CreateTestRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Unified Endpoint to Create a Master Test.
    Handles AI Generation, Visibility Logic, and Persistence.
    """
    
    # 1. Validation
    if request.visibility == "CLASSROOM" and not request.classroom_id:
        raise HTTPException(status_code=400, detail="Classroom ID required for classroom tests")

    total_questions = sum(s.count for s in request.subject_inputs.values())
    if total_questions < 1:
        raise HTTPException(status_code=400, detail="At least 1 question required")

    # 2. Determine Metadata
    active_subjects = [s for s, c in request.subject_inputs.items() if c.count > 0]
    
    if len(active_subjects) == 1:
        subject = active_subjects[0]
        # Get first topic
        topics = request.subject_inputs[subject].topics
        main_topic = topics[0] if topics else "General"
        title = f"{subject}: {main_topic} Practice"
    else:
        subject = "Mixed"
        title = f"Full Mock: {request.exam_type}"

    all_topics = []
    for data in request.subject_inputs.values():
        all_topics.extend(data.topics)

    # 3. Generate Questions (Parallel)
    tasks = []
    task_metadata = []
    
    for subj_name, config in request.subject_inputs.items():
        if config.count <= 0: continue
        
        # Prepare params
        diff_dist = config.difficulty
        subj_topics = config.topics if config.topics else ["General"]
        topic_str = ", ".join(subj_topics)
        
        levels = [
            ("Easy", int(diff_dist.get("easy", 0))),
            ("Medium", int(diff_dist.get("medium", 0))),
            ("Hard", int(diff_dist.get("hard", 0)))
        ]
        
        for diff_name, diff_count in levels:
            if diff_count > 0:
                tasks.append(llm_engine.generate_with_fallback_async(
                    subject=subj_name,
                    topic=topic_str,
                    mcq_count=diff_count,
                    numerical_count=0,
                    level=request.exam_type,
                    difficulty=diff_name
                ))
                task_metadata.append({
                    "subject": subj_name,
                    "difficulty": diff_name,
                    "topics": subj_topics,
                    "count": diff_count
                })

    print(f"Starting {len(tasks)} generation tasks for Master Test...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_questions = []
    
    for i, result in enumerate(results):
        meta = task_metadata[i]
        
        # Error Handling / Fallback
        if isinstance(result, Exception) or not result or not result.get("success"):
            print(f"Generation Failed for {meta['subject']} {meta['difficulty']}")
            # Fallback Placeholders
            for _ in range(meta['count']):
                final_questions.append({
                    "text": f"Error generating question for {meta['subject']}",
                    "options": ["Error", "Error", "Error", "Error"], # Engine expects list here usually, standardized below
                    "answer": "A",
                    "marks": 4,
                    "type": "mcq",
                    "difficulty": meta['difficulty'],
                    "subject": meta['subject'],
                    "topic": meta['topics'][0]
                })
            continue
            
        # Success
        generated = result.get("questions", [])
        # Enrich
        for q in generated:
            q["subject"] = meta["subject"]
            q["topic"] = meta["topics"][0]
            q["difficulty"] = meta["difficulty"]
            
        final_questions.extend(generated)
        
        # Partial fill
        remaining = meta['count'] - len(generated)
        if remaining > 0:
             for _ in range(remaining):
                final_questions.append({
                    "text": "Partial generation error placeholder",
                    "options": ["A", "B", "C", "D"],
                    "answer": "A",
                    "marks": 4, 
                    "subject": meta['subject'],
                    "topic": meta['topics'][0],
                    "difficulty": meta['difficulty']
                })

    # 4. Finalize Test Object
    
    # Determine Status
    status_val = "published"
    is_generated = False
    
    if request.visibility == "COMMUNITY":
        # Community tests require approval? For now, let's auto-approve or pending?
        # Plan said pending_review.
        # But for User "Everyone" logic, maybe strict pending if we want moderation.
        # Let's stick to plan: pending_review
        status_val = "pending_review"
    elif request.visibility == "PRIVATE":
        status_val = "published"
        is_generated = True # It's a personal generation
    elif request.visibility == "CLASSROOM":
        status_val = "published"

    # Share Code (for Classroom)
    share_code = None
    if request.visibility == "CLASSROOM":
        share_code = str(uuid.uuid4())[:8].upper()

    new_test = Test(
        title=title,
        creator_id=current_user.id,
        subject=subject,
        topics_json=json.dumps(all_topics),
        exam_type=request.exam_type,
        difficulty="Mixed",
        total_questions=len(final_questions),
        total_marks=sum(q.get("marks", 4) for q in final_questions),
        duration_minutes=request.duration_minutes,
        questions_data=json.dumps(final_questions),
        
        visibility_type=request.visibility,
        status=status_val,
        classroom_id=request.classroom_id,
        share_code=share_code,
        is_generated_practice=is_generated
    )
    
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    
    return {
        "test_id": new_test.id,
        "message": "Test Created Successfully",
        "status": status_val
    }

@router.get("/my", response_model=List[MyTestSchema])
def get_my_tests(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get tests created by the current user."""
    tests = db.query(Test).filter(
        Test.creator_id == current_user.id
    ).order_by(Test.created_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "title": t.title,
            "subject": t.subject,
            "created_at": t.created_at,
            "attempt_count": t.attempt_count,
            "visibility": t.visibility_type,
            "status": t.status
        }
        for t in tests
    ]

@router.patch("/{test_id}/approve")
def approve_test(
    test_id: str,
    # In real app, check admin role. checking email for simple auth now?
    # Or just allow logic for now (assuming admin middleware handles route protection if added)
    current_user: User = Depends(get_current_user_required), 
    db: Session = Depends(get_db)
):
    """Admin: Approve a community test."""
    # TODO: Add Admin Check
    
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
        
    test.status = "published"
    db.commit()
    
    return {"message": "Test approved"}
