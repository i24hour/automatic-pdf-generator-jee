from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import json
import asyncio

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

# Updated Request Schema to match Test Portal capabilities
class SubjectInput(BaseModel):
    """Configuration for a specific subject."""
    count: int
    difficulty: dict  # {"easy": 20, "medium": 50, "hard": 30}
    topics: List[str]  # ["Topic 1", "Topic 2"]

class CreatePublicTestRequest(BaseModel):
    subject_inputs: Dict[str, SubjectInput]  # {"Physics": SubjectInput, ...}
    duration_minutes: int
    exam_type: str = "JEE_MAINS" # Added for context
    
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
        # For multi-subject tests, 'subject' col might be "Mixed" or primary subject
        # We'll search mostly by exam_type or title for now
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
async def create_public_test(
    request: CreatePublicTestRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Save a generated test as a public community test."""
    
    final_questions = []
    
    # 1. Calculate total questions and topics
    total_questions = sum(s.count for s in request.subject_inputs.values())
    all_topics = []
    for data in request.subject_inputs.values():
        all_topics.extend(data.topics)
    
    if total_questions < 1:
        raise HTTPException(status_code=400, detail="At least 1 question required")

    # 2. Check if questions provided directly, else Generate
    if request.questions_data:
        final_questions = request.questions_data
    else:
        # Parallel Generation Logic (Copied from test_router)
        tasks = []
        task_metadata = []
        
        for subject, config in request.subject_inputs.items():
            count = config.count
            if count <= 0: continue
            
            difficulty_dist = config.difficulty
            subject_topics = config.topics if config.topics else ["General"]
            topic_str = ", ".join(subject_topics)
            
            # Use exact counts
            easy_count = int(difficulty_dist.get("easy", 0))
            medium_count = int(difficulty_dist.get("medium", 0))
            hard_count = int(difficulty_dist.get("hard", 0))
            
            levels = [("Easy", easy_count), ("Medium", medium_count), ("Hard", hard_count)]
            
            for diff_name, diff_count in levels:
                if diff_count > 0:
                    tasks.append(llm_engine.generate_with_fallback_async(
                        subject=subject,
                        topic=topic_str,
                        mcq_count=diff_count,
                        numerical_count=0,
                        level=request.exam_type,
                        difficulty=diff_name
                    ))
                    task_metadata.append({
                        "subject": subject, 
                        "difficulty": diff_name, 
                        "topics": subject_topics,
                        "count": diff_count
                    })

        # Execute parallel tasks
        print(f"[Community] Starting {len(tasks)} generation tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            meta = task_metadata[i]
            
            # Handle Failure
            if isinstance(result, Exception) or (isinstance(result, dict) and not result.get("success")):
                print(f"Task failed for {meta['subject']} {meta['difficulty']}")
                # create placeholder questions locally if needed, or skip
                # For public tests, we prefer skipping broken ones or retrying, but for now we skip to avoid bad data
                # Or better: generate simple fallback structure
                fallback_qs = [{
                   "text": f"Error generating question for {meta['subject']}",
                   "options": {"A": "Error", "B": "Error", "C": "Error", "D": "Error"},
                   "answer": "A",
                   "marks": 4,
                   "type": "mcq",
                   "difficulty": meta['difficulty'],
                   "subject": meta['subject'],
                   "topic": meta['topics'][0]
                }] * meta['count']
                final_questions.extend(fallback_qs)
                continue

            generated_qs = result.get("questions", [])
            # Enrich with subject/topic info if missing
            for q in generated_qs:
                if "subject" not in q: q["subject"] = meta["subject"]
                if "topic" not in q: q["topic"] = meta["topics"][0]
                if "difficulty" not in q: q["difficulty"] = meta["difficulty"]
            
            final_questions.extend(generated_qs)
    
    # Calculate metadata
    total_marks = sum(q.get("marks", 4) for q in final_questions)
    
    # Determine Title
    active_subjects = [s for s, c in request.subject_inputs.items() if c.count > 0]
    if len(active_subjects) == 1:
        # Single Subject
        main_topic = request.subject_inputs[active_subjects[0]].topics[0] if request.subject_inputs[active_subjects[0]].topics else "General"
        title = f"{active_subjects[0]}: {main_topic} Practice"
        subject_label = active_subjects[0]
    else:
        # Multi Subject
        title = f"Full Mock: {request.exam_type} Practice"
        subject_label = "Mixed"
    
    # 3. Create Test Record
    new_test = Test(
        title=title,
        creator_id=current_user.id,
        subject=subject_label,
        topics_json=json.dumps(all_topics),
        exam_type=request.exam_type,
        difficulty="Mixed", # Since it's detailed distribution
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
        
    # 2. Create Test Attempt
    try:
        # 3. Populate Questions from Master
        if not test.questions_data:
             raise ValueError("Test has no questions data")
             
        questions = json.loads(test.questions_data)
        
        # Calculate real subject distribution from questions
        subject_counts = {}
        for q in questions:
            subj = q.get("subject", test.subject) or "General"
            subject_counts[subj] = subject_counts.get(subj, 0) + 1

        attempt = TestAttempt(
            user_id=current_user.id,
            test_id=test.id, # Link to master test
            exam_type=test.exam_type,
            total_questions=test.total_questions,
            duration_minutes=test.duration_minutes,
            topics_json=test.topics_json,
            subject_distribution_json=json.dumps(subject_counts),
            status="NOT_STARTED"
        )
        db.add(attempt)
        db.flush() # Get ID
        
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
                subject=q_data.get("subject", test.subject) or "General", # Fallback for missing subject
                topic=q_data.get("topic", test.title),
                difficulty=q_data.get("difficulty", test.difficulty),
                question_type=q_data.get("type", "mcq"),
                question_text=q_data.get("question_text", q_data.get("text", "Question text missing")),
                options_json=json.dumps(options_dict),
                correct_answer=correct_ans,
                marks_correct=marks,
                marks_wrong=-1,
                status="NOT_VISITED",
                diagram_json=json.dumps(q_data.get("diagram_spec")) if q_data.get("diagram_spec") else None
            )
            db.add(response)
            
        # Increment attempt count on master test
        test.attempt_count += 1
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Error starting test {test_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Cannot start this test (Data Corrupted). Please create a new test. Error: {str(e)}")
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
            subject=q_data.get("subject", test.subject), # Use question's subject if available
            topic=q_data.get("topic", test.title),
            difficulty=q_data.get("difficulty", test.difficulty),
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
