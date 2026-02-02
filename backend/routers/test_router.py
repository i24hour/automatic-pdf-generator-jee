"""
Test Portal Router - NTA CBT-style test interface APIs.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user_required
from models import User, TestAttempt, QuestionResponse

router = APIRouter(prefix="/test", tags=["Test Portal"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateTestRequest(BaseModel):
    """Request to create a new test."""
    exam_type: str  # JEE_MAINS, JEE_ADV, NEET, CUSTOM
    topics: List[str]  # List of topic names
    subject_distribution: dict  # {"Physics": 10, "Chemistry": 10, "Maths": 10}
    difficulty_distribution: dict  # {"easy": 20, "medium": 50, "hard": 30}
    duration_minutes: int  # Test duration


class TestCreatedResponse(BaseModel):
    """Response after test creation."""
    test_id: str
    total_questions: int
    duration_minutes: int
    redirect_url: str


class QuestionData(BaseModel):
    """Single question data for frontend."""
    question_index: int
    total_questions: int
    subject: str
    topic: str
    difficulty: str
    question_type: str
    question_text: str
    options: Optional[dict] = None
    status: str
    user_answer: Optional[str] = None
    is_marked_for_review: bool
    time_remaining_seconds: int


class ActionRequest(BaseModel):
    """Request for button actions in CBT interface."""
    question_index: int
    action: str  # SAVE_NEXT, CLEAR, SAVE_MARK_NEXT, MARK_NEXT, BACK, NEXT, JUMP
    selected_answer: Optional[str] = None
    time_spent_seconds: Optional[int] = 0
    jump_to_index: Optional[int] = None  # For palette clicks


class ActionResponse(BaseModel):
    """Response after action."""
    next_question_index: int
    new_status: str


class ExamSummary(BaseModel):
    """Pre-submission exam summary."""
    total: int
    answered: int
    not_answered: int
    marked_review: int
    answered_marked: int
    not_visited: int


class PaletteItem(BaseModel):
    """Question palette item."""
    index: int
    status: str
    subject: str


class TestStateResponse(BaseModel):
    """Full test state for frontend."""
    test_id: str
    exam_type: str
    status: str
    current_question_index: int
    total_questions: int
    duration_minutes: int
    time_remaining_seconds: int
    palette: List[PaletteItem]
    subjects: List[str]


class SubmitResponse(BaseModel):
    """Response after test submission."""
    test_id: str
    total_score: int
    max_score: int
    correct_count: int
    wrong_count: int
    unattempted_count: int
    redirect_url: str


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_time_remaining(test: TestAttempt) -> int:
    """Calculate remaining time in seconds."""
    if not test.started_at:
        return test.duration_minutes * 60
    
    elapsed = (datetime.now(timezone.utc) - test.started_at).total_seconds()
    remaining = (test.duration_minutes * 60) - elapsed
    return max(0, int(remaining))


def get_question_status(response: QuestionResponse) -> str:
    """Determine NTA 5-state status for a question."""
    if response.status == "NOT_VISITED":
        return "NOT_VISITED"
    
    has_answer = response.user_answer is not None and response.user_answer != ""
    is_marked = response.is_marked_for_review
    
    if has_answer and is_marked:
        return "ANSWERED_MARKED"
    elif has_answer:
        return "ANSWERED"
    elif is_marked:
        return "MARKED_REVIEW"
    else:
        return "NOT_ANSWERED"


# ============================================
# ENDPOINTS
# ============================================

@router.post("/create", response_model=TestCreatedResponse)
async def create_test(
    request: CreateTestRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Create a new test with AI-generated questions."""
    
    # Calculate total questions from subject distribution
    total_questions = sum(request.subject_distribution.values())
    
    if total_questions < 1:
        raise HTTPException(status_code=400, detail="At least 1 question required")
    if total_questions > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 questions allowed")
    
    # Create test attempt
    test = TestAttempt(
        user_id=current_user.id,
        exam_type=request.exam_type,
        total_questions=total_questions,
        duration_minutes=request.duration_minutes,
        topics_json=json.dumps(request.topics),
        subject_distribution_json=json.dumps(request.subject_distribution),
        difficulty_distribution_json=json.dumps(request.difficulty_distribution),
        status="NOT_STARTED"
    )
    db.add(test)
    db.flush()  # Get test ID
    
    # TODO: Generate questions using existing LLM engine
    # For now, create placeholder questions
    questions = []
    q_index = 0
    
    for subject, count in request.subject_distribution.items():
        for i in range(count):
            # Determine difficulty based on distribution
            easy_pct = request.difficulty_distribution.get("easy", 30)
            medium_pct = request.difficulty_distribution.get("medium", 50)
            
            if i < count * easy_pct / 100:
                difficulty = "Easy"
            elif i < count * (easy_pct + medium_pct) / 100:
                difficulty = "Medium"
            else:
                difficulty = "Hard"
            
            topic = request.topics[i % len(request.topics)] if request.topics else "General"
            
            response = QuestionResponse(
                test_attempt_id=test.id,
                question_index=q_index,
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                question_type="mcq",
                question_text=f"[AI Question will be generated here - {subject} Q{i+1}]",
                options_json=json.dumps({
                    "A": "Option A",
                    "B": "Option B", 
                    "C": "Option C",
                    "D": "Option D"
                }),
                correct_answer="A",
                marks_correct=4,
                marks_wrong=-1 if request.exam_type != "NEET" else -1,
                status="NOT_VISITED"
            )
            db.add(response)
            q_index += 1
    
    db.commit()
    
    return TestCreatedResponse(
        test_id=test.id,
        total_questions=total_questions,
        duration_minutes=request.duration_minutes,
        redirect_url=f"/test/{test.id}/instructions"
    )


@router.get("/{test_id}/state", response_model=TestStateResponse)
async def get_test_state(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get full test state including palette."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get all responses for palette
    responses = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id
    ).order_by(QuestionResponse.question_index).all()
    
    palette = [
        PaletteItem(
            index=r.question_index,
            status=get_question_status(r),
            subject=r.subject
        )
        for r in responses
    ]
    
    # Get unique subjects
    subjects = list(dict.fromkeys([r.subject for r in responses]))
    
    return TestStateResponse(
        test_id=test.id,
        exam_type=test.exam_type,
        status=test.status,
        current_question_index=test.current_question_index,
        total_questions=test.total_questions,
        duration_minutes=test.duration_minutes,
        time_remaining_seconds=calculate_time_remaining(test),
        palette=palette,
        subjects=subjects
    )


@router.post("/{test_id}/start")
async def start_test(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Start the test (after instructions accepted)."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if test.status != "NOT_STARTED":
        raise HTTPException(status_code=400, detail="Test already started")
    
    test.status = "IN_PROGRESS"
    test.started_at = datetime.now(timezone.utc)
    
    # Mark first question as visited
    first_q = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id,
        QuestionResponse.question_index == 0
    ).first()
    if first_q:
        first_q.status = "NOT_ANSWERED"
        first_q.last_visited_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "Test started", "redirect_url": f"/test/{test_id}"}


@router.get("/{test_id}/question/{index}", response_model=QuestionData)
async def get_question(
    test_id: str,
    index: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get a specific question by index."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if test.status not in ["IN_PROGRESS", "NOT_STARTED"]:
        raise HTTPException(status_code=400, detail="Test not in progress")
    
    response = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id,
        QuestionResponse.question_index == index
    ).first()
    
    if not response:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Mark as visited if first time
    if response.status == "NOT_VISITED":
        response.status = "NOT_ANSWERED"
        response.last_visited_at = datetime.now(timezone.utc)
        db.commit()
    
    # Update current question index
    test.current_question_index = index
    db.commit()
    
    options = json.loads(response.options_json) if response.options_json else None
    
    return QuestionData(
        question_index=response.question_index,
        total_questions=test.total_questions,
        subject=response.subject,
        topic=response.topic,
        difficulty=response.difficulty,
        question_type=response.question_type,
        question_text=response.question_text,
        options=options,
        status=get_question_status(response),
        user_answer=response.user_answer,
        is_marked_for_review=response.is_marked_for_review,
        time_remaining_seconds=calculate_time_remaining(test)
    )


@router.post("/{test_id}/action", response_model=ActionResponse)
async def handle_action(
    test_id: str,
    request: ActionRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Handle NTA button actions: SAVE_NEXT, CLEAR, SAVE_MARK_NEXT, MARK_NEXT, BACK, NEXT, JUMP."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id,
        TestAttempt.status == "IN_PROGRESS"
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found or not in progress")
    
    response = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id,
        QuestionResponse.question_index == request.question_index
    ).first()
    
    if not response:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Update time spent
    if request.time_spent_seconds:
        response.time_spent_seconds += request.time_spent_seconds
    
    # Handle action
    next_index = request.question_index
    
    if request.action == "SAVE_NEXT":
        if request.selected_answer:
            response.user_answer = request.selected_answer
        response.status = get_question_status(response)
        next_index = min(request.question_index + 1, test.total_questions - 1)
        
    elif request.action == "CLEAR":
        response.user_answer = None
        response.status = "NOT_ANSWERED" if not response.is_marked_for_review else "MARKED_REVIEW"
        
    elif request.action == "SAVE_MARK_NEXT":
        if request.selected_answer:
            response.user_answer = request.selected_answer
        response.is_marked_for_review = True
        response.status = get_question_status(response)
        next_index = min(request.question_index + 1, test.total_questions - 1)
        
    elif request.action == "MARK_NEXT":
        response.is_marked_for_review = True
        response.status = get_question_status(response)
        next_index = min(request.question_index + 1, test.total_questions - 1)
        
    elif request.action == "BACK":
        next_index = max(0, request.question_index - 1)
        
    elif request.action == "NEXT":
        next_index = min(request.question_index + 1, test.total_questions - 1)
        
    elif request.action == "JUMP":
        if request.jump_to_index is not None:
            next_index = max(0, min(request.jump_to_index, test.total_questions - 1))
    
    # Update current question index
    test.current_question_index = next_index
    
    # Mark next question as visited
    if next_index != request.question_index:
        next_response = db.query(QuestionResponse).filter(
            QuestionResponse.test_attempt_id == test_id,
            QuestionResponse.question_index == next_index
        ).first()
        if next_response and next_response.status == "NOT_VISITED":
            next_response.status = "NOT_ANSWERED"
            next_response.last_visited_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return ActionResponse(
        next_question_index=next_index,
        new_status=get_question_status(response)
    )


@router.get("/{test_id}/summary", response_model=ExamSummary)
async def get_exam_summary(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get exam summary before submission."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    responses = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id
    ).all()
    
    counts = {
        "answered": 0,
        "not_answered": 0,
        "marked_review": 0,
        "answered_marked": 0,
        "not_visited": 0
    }
    
    for r in responses:
        status = get_question_status(r)
        if status == "ANSWERED":
            counts["answered"] += 1
        elif status == "NOT_ANSWERED":
            counts["not_answered"] += 1
        elif status == "MARKED_REVIEW":
            counts["marked_review"] += 1
        elif status == "ANSWERED_MARKED":
            counts["answered_marked"] += 1
        elif status == "NOT_VISITED":
            counts["not_visited"] += 1
    
    return ExamSummary(
        total=test.total_questions,
        **counts
    )


@router.post("/{test_id}/submit", response_model=SubmitResponse)
async def submit_test(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Submit test and calculate score."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if test.status == "SUBMITTED":
        raise HTTPException(status_code=400, detail="Test already submitted")
    
    # Calculate score
    responses = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id
    ).all()
    
    total_score = 0
    max_score = 0
    correct_count = 0
    wrong_count = 0
    unattempted_count = 0
    
    for r in responses:
        max_score += r.marks_correct
        
        if r.user_answer is None or r.user_answer == "":
            unattempted_count += 1
            r.is_correct = None
            r.marks_obtained = 0
        elif r.user_answer == r.correct_answer:
            correct_count += 1
            total_score += r.marks_correct
            r.is_correct = True
            r.marks_obtained = r.marks_correct
        else:
            wrong_count += 1
            total_score += r.marks_wrong
            r.is_correct = False
            r.marks_obtained = r.marks_wrong
    
    # Update test
    test.status = "SUBMITTED"
    test.submitted_at = datetime.now(timezone.utc)
    test.total_score = total_score
    test.max_score = max_score
    test.correct_count = correct_count
    test.wrong_count = wrong_count
    test.unattempted_count = unattempted_count
    
    db.commit()
    
    return SubmitResponse(
        test_id=test.id,
        total_score=total_score,
        max_score=max_score,
        correct_count=correct_count,
        wrong_count=wrong_count,
        unattempted_count=unattempted_count,
        redirect_url=f"/test/{test_id}/result"
    )


@router.get("/{test_id}/result")
async def get_result(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get detailed test result with analytics."""
    test = db.query(TestAttempt).filter(
        TestAttempt.id == test_id,
        TestAttempt.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if test.status != "SUBMITTED":
        raise HTTPException(status_code=400, detail="Test not submitted yet")
    
    responses = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id
    ).order_by(QuestionResponse.question_index).all()
    
    # Subject-wise analysis
    subject_analysis = {}
    for r in responses:
        if r.subject not in subject_analysis:
            subject_analysis[r.subject] = {
                "correct": 0,
                "wrong": 0,
                "unattempted": 0,
                "score": 0,
                "max_score": 0,
                "time_spent": 0
            }
        
        subject_analysis[r.subject]["max_score"] += r.marks_correct
        subject_analysis[r.subject]["time_spent"] += r.time_spent_seconds
        
        if r.is_correct is True:
            subject_analysis[r.subject]["correct"] += 1
            subject_analysis[r.subject]["score"] += r.marks_correct
        elif r.is_correct is False:
            subject_analysis[r.subject]["wrong"] += 1
            subject_analysis[r.subject]["score"] += r.marks_wrong
        else:
            subject_analysis[r.subject]["unattempted"] += 1
    
    # Calculate accuracy per subject
    for subj in subject_analysis:
        attempted = subject_analysis[subj]["correct"] + subject_analysis[subj]["wrong"]
        if attempted > 0:
            subject_analysis[subj]["accuracy"] = round(
                subject_analysis[subj]["correct"] / attempted * 100, 1
            )
        else:
            subject_analysis[subj]["accuracy"] = 0
    
    return {
        "test_id": test.id,
        "exam_type": test.exam_type,
        "total_score": test.total_score,
        "max_score": test.max_score,
        "correct_count": test.correct_count,
        "wrong_count": test.wrong_count,
        "unattempted_count": test.unattempted_count,
        "percentage": round(test.total_score / test.max_score * 100, 1) if test.max_score > 0 else 0,
        "started_at": test.started_at.isoformat() if test.started_at else None,
        "submitted_at": test.submitted_at.isoformat() if test.submitted_at else None,
        "duration_taken_minutes": round((test.submitted_at - test.started_at).total_seconds() / 60, 1) if test.started_at and test.submitted_at else None,
        "subject_analysis": subject_analysis,
        "questions": [
            {
                "index": r.question_index,
                "subject": r.subject,
                "topic": r.topic,
                "difficulty": r.difficulty,
                "question_text": r.question_text,
                "options": json.loads(r.options_json) if r.options_json else None,
                "correct_answer": r.correct_answer,
                "user_answer": r.user_answer,
                "is_correct": r.is_correct,
                "marks_obtained": r.marks_obtained,
                "time_spent_seconds": r.time_spent_seconds,
                "solution": r.solution
            }
            for r in responses
        ]
    }


@router.get("/history")
async def get_test_history(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get user's test history."""
    tests = db.query(TestAttempt).filter(
        TestAttempt.user_id == current_user.id
    ).order_by(TestAttempt.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": t.id,
            "exam_type": t.exam_type,
            "total_questions": t.total_questions,
            "duration_minutes": t.duration_minutes,
            "status": t.status,
            "total_score": t.total_score,
            "max_score": t.max_score,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None
        }
        for t in tests
    ]
