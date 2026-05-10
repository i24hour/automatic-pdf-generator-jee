from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import asyncio
import uuid

from database import get_db, SessionLocal
from models import User, Test, generate_uuid
from auth import get_current_user_required, decode_token
from services.llm_engine import llm_engine
from services.job_store import job_store, JobStatus

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

    # 3. Generate Questions (Parallel) — 1 LLM call per subject (NOT per difficulty level)
    # Combining all difficulty tiers into one call per subject cuts API round trips by ~3x.
    tasks = []
    task_metadata = []
    
    for subj_name, config in request.subject_inputs.items():
        if config.count <= 0: continue
        
        diff_dist = config.difficulty
        subj_topics = config.topics if config.topics else ["General"]
        topic_str = ", ".join(subj_topics)
        
        easy_count   = int(diff_dist.get("easy", 0))
        medium_count = int(diff_dist.get("medium", 0))
        hard_count   = int(diff_dist.get("hard", 0))
        total_count  = config.count

        # Derive percentage distribution for the prompt
        easy_pct   = round(easy_count   / total_count * 100) if total_count else 20
        medium_pct = round(medium_count / total_count * 100) if total_count else 50
        hard_pct   = 100 - easy_pct - medium_pct  # ensure sum == 100

        # Split MCQ vs Numerical by exam type (NEET = all MCQ)
        if request.exam_type in ["JEE_MAINS", "JEE_ADV", "CUSTOM"]:
            num_numerical = round(total_count * 0.2)
            num_mcq = total_count - num_numerical
        else:  # NEET
            num_numerical = 0
            num_mcq = total_count

        tasks.append(llm_engine.generate_parallel(
            subject=subj_name,
            topic=topic_str,
            mcq_count=num_mcq,
            numerical_count=num_numerical,
            level=request.exam_type,
            difficulty="Mixed",
            easy_percent=easy_pct,
            medium_percent=medium_pct,
            hard_percent=hard_pct,
            include_solutions=False,
            chunk_size=10
        ))
        task_metadata.append({
            "subject": subj_name,
            "topics": subj_topics,
            "count": total_count,
        })

    print(f"Starting {len(tasks)} generation tasks (1 per subject) for Master Test...")
    # Wrap gather in a timeout so a slow/hung LLM call returns a clean JSON 504 rather
    # than causing the proxy to time out and return an HTML error page.
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=240  # 4-minute hard cap; subjects fall back to placeholders individually
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Question generation timed out. Please try again."
        )

    
    final_questions = []
    
    for i, result in enumerate(results):
        meta = task_metadata[i]
        
        # Error Handling / Fallback
        if isinstance(result, Exception) or not result or not result.get("success"):
            print(f"Generation Failed for {meta['subject']}: {result}")
            # Fallback Placeholders
            for _ in range(meta['count']):
                final_questions.append({
                    "text": f"Error generating question for {meta['subject']}",
                    "options": ["Error", "Error", "Error", "Error"],
                    "answer": "A",
                    "marks": 4,
                    "type": "mcq",
                    "difficulty": "Medium",
                    "subject": meta['subject'],
                    "topic": meta['topics'][0]
                })
            continue
            
        # Success
        generated = result.get("questions", [])
        # Enrich with subject and topic (difficulty comes from the LLM result itself)
        for q in generated:
            q["subject"] = meta["subject"]
            q.setdefault("topic", meta["topics"][0])
            q.setdefault("difficulty", "Medium")
            
        final_questions.extend(generated)
        
        # Partial fill if LLM returned fewer questions than requested
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
                    "difficulty": "Medium"
                })


    # Sort final_questions: MCQs first, then numericals
    mcq_questions = [q for q in final_questions if q.get("type") != "numerical"]
    num_questions = [q for q in final_questions if q.get("type") == "numerical"]
    final_questions = mcq_questions + num_questions

    # 4. Finalize Test Object
    
    # Determine Status
    status_val = "published"
    is_generated = False
    
    if request.visibility == "COMMUNITY":
        # Community tests require approval? For now, we auto-approve so they show up.
        status_val = "published"
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


# ============== SSE-BASED ASYNC TEST CREATION ==============

class TestSSEStartResponse(BaseModel):
    """Response for async test creation start."""
    job_id: str
    message: str


@router.post("/create-async", response_model=TestSSEStartResponse)
async def create_test_async(
    request: CreateTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_required),
):
    """
    Start test creation as a background job and return job_id instantly.
    Frontend connects to /api/tests/{job_id}/stream for SSE progress.
    This avoids Vercel proxy timeouts on long LLM generation calls.
    """
    # Validation (same as sync create)
    if request.visibility == "CLASSROOM" and not request.classroom_id:
        raise HTTPException(status_code=400, detail="Classroom ID required for classroom tests")

    total_questions = sum(s.count for s in request.subject_inputs.values())
    if total_questions < 1:
        raise HTTPException(status_code=400, detail="At least 1 question required")

    # Create job
    job = job_store.create_job(str(current_user.id))

    # Pass only serializable data — db and User are request-scoped and will be
    # closed before the background task runs. The task opens its own session.
    background_tasks.add_task(
        run_test_creation_job,
        job.job_id,
        request,
        str(current_user.id),
    )

    return TestSSEStartResponse(
        job_id=job.job_id,
        message="Test creation started. Connect to SSE stream for progress."
    )


async def run_test_creation_job(
    job_id: str,
    request: CreateTestRequest,
    user_id: str,
):
    """Background task that generates questions and creates the test, streaming progress via job_store.
    
    Opens its own DB session — never reuse the request-scoped session, which is
    closed by FastAPI as soon as the /create-async response is sent.
    """
    from database import SessionLocal
    from models import User
    
    db = SessionLocal()
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            job_store.update_job(
                job_id, status=JobStatus.FAILED, progress=0,
                message="User not found", error="User not found"
            )
            return
        
        # Step 1: Analyzing
        job_store.update_job(job_id, status=JobStatus.ANALYZING, progress=5, message="Analyzing request...")

        # Determine metadata
        active_subjects = [s for s, c in request.subject_inputs.items() if c.count > 0]

        if len(active_subjects) == 1:
            subject = active_subjects[0]
            topics = request.subject_inputs[subject].topics
            main_topic = topics[0] if topics else "General"
            title = f"{subject}: {main_topic} Practice"
        else:
            subject = "Mixed"
            title = f"Full Mock: {request.exam_type}"

        all_topics = []
        for data in request.subject_inputs.values():
            all_topics.extend(data.topics)

        # Step 2: Generate questions per subject (sequential with progress)
        job_store.update_job(job_id, status=JobStatus.GENERATING_MCQS, progress=10, message="Generating questions...")

        tasks = []
        task_metadata = []

        for subj_name, config in request.subject_inputs.items():
            if config.count <= 0:
                continue

            diff_dist = config.difficulty
            subj_topics = config.topics if config.topics else ["General"]
            topic_str = ", ".join(subj_topics)

            easy_count = int(diff_dist.get("easy", 0))
            medium_count = int(diff_dist.get("medium", 0))
            hard_count = int(diff_dist.get("hard", 0))
            total_count = config.count

            easy_pct = round(easy_count / total_count * 100) if total_count else 20
            medium_pct = round(medium_count / total_count * 100) if total_count else 50
            hard_pct = 100 - easy_pct - medium_pct

            if request.exam_type in ["JEE_MAINS", "JEE_ADV", "CUSTOM"]:
                num_numerical = round(total_count * 0.2)
                num_mcq = total_count - num_numerical
            else:  # NEET
                num_numerical = 0
                num_mcq = total_count

            tasks.append(llm_engine.generate_parallel(
                subject=subj_name,
                topic=topic_str,
                mcq_count=num_mcq,
                numerical_count=num_numerical,
                level=request.exam_type,
                difficulty="Mixed",
                easy_percent=easy_pct,
                medium_percent=medium_pct,
                hard_percent=hard_pct,
                include_solutions=False,
                chunk_size=10
            ))
            task_metadata.append({
                "subject": subj_name,
                "topics": subj_topics,
                "count": total_count,
            })

        # Run generation with per-subject progress updates
        total_subjects = len(tasks)
        final_questions = []

        for i, (task, meta) in enumerate(zip(tasks, task_metadata)):
            subj_progress = 10 + int((i / total_subjects) * 70)  # 10-80%
            job_store.update_job(
                job_id,
                progress=subj_progress,
                message=f"Generating {meta['subject']} ({i+1}/{total_subjects})..."
            )

            try:
                result = await asyncio.wait_for(task, timeout=120)  # 2 min per subject
            except asyncio.TimeoutError:
                result = None

            if isinstance(result, Exception) or not result or not result.get("success"):
                print(f"[TestSSE] Generation failed for {meta['subject']}: {result}")
                for _ in range(meta['count']):
                    final_questions.append({
                        "text": f"Error generating question for {meta['subject']}",
                        "options": ["Error", "Error", "Error", "Error"],
                        "answer": "A", "marks": 4, "type": "mcq",
                        "difficulty": "Medium",
                        "subject": meta['subject'],
                        "topic": meta['topics'][0]
                    })
                continue

            generated = result.get("questions", [])
            for q in generated:
                q["subject"] = meta["subject"]
                q.setdefault("topic", meta["topics"][0])
                q.setdefault("difficulty", "Medium")

            final_questions.extend(generated)

            remaining = meta['count'] - len(generated)
            if remaining > 0:
                for _ in range(remaining):
                    final_questions.append({
                        "text": "Partial generation error placeholder",
                        "options": ["A", "B", "C", "D"],
                        "answer": "A", "marks": 4,
                        "subject": meta['subject'],
                        "topic": meta['topics'][0],
                        "difficulty": "Medium"
                    })

            # Update progress after each subject completes
            job_store.update_job(
                job_id,
                progress=10 + int(((i + 1) / total_subjects) * 70),
                message=f"{meta['subject']} done ({i+1}/{total_subjects})"
            )

        # Step 3: Finalize
        job_store.update_job(job_id, progress=85, message="Sorting & finalizing test...")

        # Sort: MCQs first, then numericals
        mcq_questions = [q for q in final_questions if q.get("type") != "numerical"]
        num_questions = [q for q in final_questions if q.get("type") == "numerical"]
        final_questions = mcq_questions + num_questions

        # Determine status
        status_val = "published"
        is_generated = request.visibility == "PRIVATE"

        share_code = None
        if request.visibility == "CLASSROOM":
            share_code = str(uuid.uuid4())[:8].upper()

        job_store.update_job(job_id, progress=90, message="Saving test to database...")

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

        # Done!
        job_store.update_job(
            job_id,
            status=JobStatus.DONE,
            progress=100,
            message="Test created successfully!",
            result={
                "test_id": new_test.id,
                "message": "Test Created Successfully",
                "status": status_val
            }
        )

    except Exception as e:
        print(f"[TestSSE] Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            message="Test creation failed",
            error=str(e)
        )
    finally:
        db.close()


@router.get("/{job_id}/stream")
async def stream_test_creation_progress(
    job_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    SSE endpoint to stream test creation progress.
    Uses token query param since EventSource doesn't support headers.
    """
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

    if job.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    async def event_generator():
        queue = job_store.subscribe(job_id)

        try:
            # Send current state first
            current_job = job_store.get_job(job_id)
            if current_job:
                yield f"data: {json.dumps(current_job.to_dict())}\n\n"

            if current_job and current_job.status in [JobStatus.DONE, JobStatus.FAILED]:
                return

            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(update)}\n\n"

                    if update.get("status") in ["done", "failed"]:
                        break
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"

                    current_job = job_store.get_job(job_id)
                    if not current_job or current_job.status in [JobStatus.DONE, JobStatus.FAILED]:
                        if current_job:
                            yield f"data: {json.dumps(current_job.to_dict())}\n\n"
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


@router.get("/{job_id}/status")
async def get_test_creation_status(
    job_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """
    Poll endpoint for test creation job status.
    Useful for reconnection after network drops.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if job.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    return job.to_dict()
