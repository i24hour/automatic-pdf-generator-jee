"""
Test Portal Router - NTA CBT-style test interface APIs.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncio

from database import get_db
from auth import get_current_user_required
from models import User, TestAttempt, QuestionResponse, TestLeaderboard, Test
from services.llm_engine import llm_engine

router = APIRouter(prefix="/test", tags=["Test Portal"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class SubjectInput(BaseModel):
    """Configuration for a specific subject."""
    count: int
    difficulty: dict  # {"easy": 20, "medium": 50, "hard": 30}
    topics: List[str]  # ["Topic 1", "Topic 2"]


class CreateTestRequest(BaseModel):
    """Request to create a new test."""
    exam_type: str  # JEE_MAINS, JEE_ADV, NEET, CUSTOM
    subject_inputs: Dict[str, SubjectInput]  # {"Physics": SubjectInput, ...}
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
    diagram_json: Optional[str] = None   # Legacy TikZ format
    diagram_svg: Optional[str] = None    # New: inline SVG string
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


class PaletteItem(BaseModel):
    """Question palette item."""
    index: int
    status: str
    subject: str


class ActionResponse(BaseModel):
    """Response after action — includes full state + next question to avoid extra API calls."""
    next_question_index: int
    new_status: str
    # Embedded test state (replaces separate GET /state call)
    palette: List[PaletteItem] = []
    subjects: List[str] = []
    time_remaining_seconds: int = 0
    # Embedded next question (replaces separate GET /question call)
    next_question: Optional[QuestionData] = None


class ExamSummary(BaseModel):
    """Pre-submission exam summary."""
    total: int
    answered: int
    not_answered: int
    marked_review: int
    answered_marked: int
    not_visited: int


class SecurityLogInput(BaseModel):
    """Security violations log sent upon force submission."""
    tabSwitchCount: int
    fullscreenExitCount: int
    devtoolsAttempts: int
    copyAttempts: int
    totalWarnings: int





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
    
    # Ensure started_at is timezone aware for calculation (SQLite stores naive)
    started_at = test.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
        
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
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

@router.post("/{test_id}/launch")
def launch_test_attempt(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Launch a new attempt for a Master Test.
    Creates a TestAttempt record linked to the Master Test.
    """
    # 1. Fetch Master Test
    master_test = db.query(Test).filter(Test.id == test_id).first()
    if not master_test:
        raise HTTPException(status_code=404, detail="Test not found")
        
    # 2. Check Permissions (Basic Visibility Check)
    if master_test.visibility_type == "PRIVATE" and master_test.creator_id != current_user.id:
        # Allow admins in future
        raise HTTPException(status_code=403, detail="Access denied to private test")
        
    # 3. Create Attempt
    try:
        questions = json.loads(master_test.questions_data)
        
        # Calculate subject distribution
        subject_counts = {}
        for q in questions:
            subj = q.get("subject", master_test.subject) or "General"
            subject_counts[subj] = subject_counts.get(subj, 0) + 1

        attempt = TestAttempt(
            user_id=current_user.id,
            test_id=master_test.id,
            exam_type=master_test.exam_type,
            total_questions=master_test.total_questions,
            duration_minutes=master_test.duration_minutes,
            topics_json=master_test.topics_json,
            subject_distribution_json=json.dumps(subject_counts),
            status="NOT_STARTED"
        )
        db.add(attempt)
        db.flush()
        
        # 4. Create Question Responses
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
            
            response = QuestionResponse(
                test_attempt_id=attempt.id,
                question_index=idx,
                subject=q_data.get("subject", master_test.subject) or "General",
                topic=q_data.get("topic", master_test.title),
                difficulty=q_data.get("difficulty", master_test.difficulty),
                question_type=q_data.get("type", "mcq"),
                question_text=q_data.get("question_text", q_data.get("text", "Question text missing")),
                options_json=json.dumps(options_dict),
                correct_answer=correct_ans,
                marks_correct=q_data.get("marks", 4),
                marks_wrong=-1,
                status="NOT_VISITED",
                # Store diagram_svg directly if available (new format), else legacy TikZ dict
                diagram_json=q_data.get("diagram_svg") or (
                    json.dumps({
                        "type": q_data.get("diagram_type"),
                        "params": q_data.get("diagram_params")
                    }) if q_data.get("diagram_type") else None
                )
            )
            db.add(response)
            
        # Increment attempt count on master
        master_test.attempt_count += 1
        db.commit()
        
        return {
            "attempt_id": attempt.id,
            "redirect_url": f"/test/{attempt.id}/instructions"
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error launching test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to launch test attempt")


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
    
    time_remaining = calculate_time_remaining(test)

    # ── Auto-submit if timer has expired ──────────────────────────────────────
    if time_remaining == 0 and test.status == "IN_PROGRESS":
        try:
            # Score all responses
            total_score = 0
            max_score = 0
            correct_count = 0
            wrong_count = 0
            unattempted_count = 0

            for r in responses:
                max_score += r.marks_correct
                if r.user_answer is None or r.user_answer == "":
                    unattempted_count += 1
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

            test.status = "SUBMITTED"
            test.submitted_at = datetime.now(timezone.utc)
            test.total_score = total_score
            test.max_score = max_score
            test.correct_count = correct_count
            test.wrong_count = wrong_count
            test.unattempted_count = unattempted_count
            db.commit()

            # Update leaderboard if this is a community test
            if test.test_id:
                total_attempted = correct_count + wrong_count
                accuracy = (correct_count / total_attempted * 100) if total_attempted > 0 else 0
                time_taken = int((test.submitted_at - test.started_at).total_seconds()) if test.started_at else test.duration_minutes * 60

                existing_entry = db.query(TestLeaderboard).filter(
                    TestLeaderboard.test_id == test.test_id,
                    TestLeaderboard.user_id == current_user.id
                ).first()

                if not existing_entry:
                    db.add(TestLeaderboard(
                        test_id=test.test_id,
                        user_id=current_user.id,
                        score=total_score,
                        time_taken_seconds=time_taken,
                        accuracy=accuracy,
                        submitted_at=datetime.now(timezone.utc)
                    ))
                elif total_score > existing_entry.score or (
                    total_score == existing_entry.score and time_taken < existing_entry.time_taken_seconds
                ):
                    existing_entry.score = total_score
                    existing_entry.time_taken_seconds = time_taken
                    existing_entry.accuracy = accuracy
                    existing_entry.submitted_at = datetime.now(timezone.utc)

                db.commit()

            print(f"⏰ Auto-submitted timed-out test {test_id} (score: {total_score}/{max_score})")

        except Exception as e:
            db.rollback()
            print(f"⚠ Auto-submit failed for test {test_id}: {e}")
    # ──────────────────────────────────────────────────────────────────────────

    return TestStateResponse(
        test_id=test.id,
        exam_type=test.exam_type,
        status=test.status,
        current_question_index=test.current_question_index,
        total_questions=test.total_questions,
        duration_minutes=test.duration_minutes,
        time_remaining_seconds=time_remaining,
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
    
    if test.status == "IN_PROGRESS":
        return {"message": "Test resumed", "redirect_url": f"/test/{test_id}"}

    if test.status != "NOT_STARTED":
        raise HTTPException(status_code=400, detail="Test already submitted or expired")
    
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

    # Detect new inline SVG format vs legacy TikZ JSON
    diagram_svg = None
    diagram_json = None
    raw_diagram = response.diagram_json
    if raw_diagram:
        if raw_diagram.strip().startswith("<svg"):
            diagram_svg = raw_diagram   # New: pass SVG directly to frontend
        else:
            diagram_json = raw_diagram  # Legacy: TikZ JSON for old renderer

    return QuestionData(
        question_index=response.question_index,
        total_questions=test.total_questions,
        subject=response.subject,
        topic=response.topic,
        difficulty=response.difficulty,
        question_type=response.question_type,
        question_text=response.question_text,
        options=options,
        diagram_json=diagram_json,
        diagram_svg=diagram_svg,
        status=get_question_status(response),
        user_answer=response.user_answer,
        is_marked_for_review=response.is_marked_for_review,
        time_remaining_seconds=calculate_time_remaining(test),
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
    next_q_response = None
    if next_index != request.question_index:
        next_q_response = db.query(QuestionResponse).filter(
            QuestionResponse.test_attempt_id == test_id,
            QuestionResponse.question_index == next_index
        ).first()
        if next_q_response and next_q_response.status == "NOT_VISITED":
            next_q_response.status = "NOT_ANSWERED"
            next_q_response.last_visited_at = datetime.now(timezone.utc)
    else:
        next_q_response = response  # Same question (e.g. CLEAR action)
    
    db.commit()
    
    # --- Build combined response (palette + next question) ---
    # 1. Palette (same logic as GET /state)
    all_responses = db.query(QuestionResponse).filter(
        QuestionResponse.test_attempt_id == test_id
    ).order_by(QuestionResponse.question_index).all()
    
    palette = [
        PaletteItem(
            index=r.question_index,
            status=get_question_status(r),
            subject=r.subject
        )
        for r in all_responses
    ]
    subjects = list(dict.fromkeys([r.subject for r in all_responses]))
    time_remaining = calculate_time_remaining(test)
    
    # 2. Next question data
    next_question_data = None
    if next_q_response:
        options = json.loads(next_q_response.options_json) if next_q_response.options_json else None
        next_question_data = QuestionData(
            question_index=next_q_response.question_index,
            total_questions=test.total_questions,
            subject=next_q_response.subject,
            topic=next_q_response.topic,
            difficulty=next_q_response.difficulty,
            question_type=next_q_response.question_type,
            question_text=next_q_response.question_text,
            options=options,
            status=get_question_status(next_q_response),
            user_answer=next_q_response.user_answer,
            is_marked_for_review=next_q_response.is_marked_for_review,
            time_remaining_seconds=time_remaining
        )
    
    return ActionResponse(
        next_question_index=next_index,
        new_status=get_question_status(response),
        palette=palette,
        subjects=subjects,
        time_remaining_seconds=time_remaining,
        next_question=next_question_data
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
    
    # --- Leaderboard Update Logic ---
    if test.test_id:
        try:
            # Check existing entry
            existing_entry = db.query(TestLeaderboard).filter(
                TestLeaderboard.test_id == test.test_id,
                TestLeaderboard.user_id == current_user.id
            ).first()
            
            # Calculate accuracy
            total_attempted = correct_count + wrong_count
            accuracy = (correct_count / total_attempted * 100) if total_attempted > 0 else 0
            time_taken = int((test.submitted_at - test.started_at).total_seconds()) if test.started_at else 0
            
            should_update = False
            
            if not existing_entry:
                should_update = True
                existing_entry = TestLeaderboard(
                    test_id=test.test_id,
                    user_id=current_user.id,
                    score=total_score,
                    time_taken_seconds=time_taken,
                    accuracy=accuracy,
                    submitted_at=datetime.now(timezone.utc)
                )
                db.add(existing_entry)
            else:
                # Update if score is better, or score equal but time is less
                if total_score > existing_entry.score:
                    should_update = True
                elif total_score == existing_entry.score and time_taken < existing_entry.time_taken_seconds:
                    should_update = True
                
                if should_update:
                    existing_entry.score = total_score
                    existing_entry.time_taken_seconds = time_taken
                    existing_entry.accuracy = accuracy
                    existing_entry.submitted_at = datetime.now(timezone.utc)
            
            if should_update:
                db.commit()
                
        except Exception as e:
            print(f"Failed to update leaderboard: {e}")
            # Don't fail the submission even if leaderboard update fails
    # --------------------------------
    
    return SubmitResponse(
        test_id=test.id,
        total_score=total_score,
        max_score=max_score,
        correct_count=correct_count,
        wrong_count=wrong_count,
        unattempted_count=unattempted_count,
        redirect_url=f"/test/{test_id}/result"
    )

@router.post("/{test_id}/violation-submit", response_model=SubmitResponse)
async def violation_submit_test(
    test_id: str,
    log: SecurityLogInput,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Force submit test due to security violations."""
    print(f"🚨 SECURITY VIOLATION SUBMIT for user {current_user.email} on test {test_id}: {log.dict()}")
    # We can just reuse the exact same scoring logic as regular submit.
    # In a full production system, we might save `log.dict()` to a dedicated SecurityViolations database table.
    return await submit_test(test_id=test_id, current_user=current_user, db=db)


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
