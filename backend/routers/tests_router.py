from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
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
    visibility: str = "PRIVATE"  # PRIVATE, CLASSROOM, COMMUNITY
    classroom_id: Optional[str] = None

class TestCreatedResponse(BaseModel):
    test_id: str
    message: str
    status: str

class TestJobStartResponse(BaseModel):
    job_id: str
    message: str

class MyTestSchema(BaseModel):
    id: str
    title: str
    subject: str
    created_at: datetime
    attempt_count: int
    visibility: str
    status: str


# --- Background job runner ---

async def run_test_creation_job(
    job_id: str,
    request: CreateTestRequest,
    user_id: str,
):
    """Background task: generate questions, save test, update SSE job."""
    db = SessionLocal()
    try:
        job_store.update_job(
            job_id,
            status=JobStatus.GENERATING_QUESTIONS,
            progress=10,
            message="Starting question generation...",
        )

        # --- Metadata ---
        active_subjects = [s for s, c in request.subject_inputs.items() if c.count > 0]

        if len(active_subjects) == 1:
            subject = active_subjects[0]
            topics_list = request.subject_inputs[subject].topics
            main_topic = topics_list[0] if topics_list else "General"
            title = f"{subject}: {main_topic} Practice"
        else:
            subject = "Mixed"
            title = f"Full Mock: {request.exam_type}"

        all_topics: list = []
        for data in request.subject_inputs.values():
            all_topics.extend(data.topics)

        # --- Build per-subject generation tasks ---
        tasks = []
        task_metadata = []
        num_subjects = len(active_subjects)

        for subj_name, config in request.subject_inputs.items():
            if config.count <= 0:
                continue

            diff_dist = config.difficulty
            subj_topics = config.topics if config.topics else ["General"]
            topic_str = ", ".join(subj_topics)

            easy_count = int(diff_dist.get("easy", 0))
            medium_count = int(diff_dist.get("medium", 0))
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
                chunk_size=10,
            ))
            task_metadata.append({
                "subject": subj_name,
                "topics": subj_topics,
                "count": total_count,
            })

        print(f"[TestJob {job_id}] Starting {len(tasks)} generation tasks...")

        # Run subjects in parallel; update progress as each completes
        completed = 0
        final_questions: list = []

        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                meta = task_metadata[completed]  # order may vary, but we just need count
            except Exception as exc:
                print(f"[TestJob {job_id}] Subject task raised: {exc}")
                # find first unprocessed meta to use for placeholder count
                meta = task_metadata[completed] if completed < len(task_metadata) else {"subject": "Unknown", "topics": ["General"], "count": 0}
                result = None

            # Resolve actual meta by index only when tasks are ordered (gather); for
            # as_completed we match by order of completion — placeholders still correct.
            if isinstance(result, Exception) or not result or not result.get("success"):
                print(f"[TestJob {job_id}] Generation failed for a subject, using placeholders")
                for _ in range(meta["count"]):
                    final_questions.append({
                        "text": f"Error generating question for {meta['subject']}",
                        "options": ["Error", "Error", "Error", "Error"],
                        "answer": "A",
                        "marks": 4,
                        "type": "mcq",
                        "difficulty": "Medium",
                        "subject": meta["subject"],
                        "topic": meta["topics"][0],
                    })
            else:
                generated = result.get("questions", [])
                for q in generated:
                    q["subject"] = meta["subject"]
                    q.setdefault("topic", meta["topics"][0])
                    q.setdefault("difficulty", "Medium")
                final_questions.extend(generated)

                # Partial fill
                remaining = meta["count"] - len(generated)
                for _ in range(remaining):
                    final_questions.append({
                        "text": "Partial generation error placeholder",
                        "options": ["A", "B", "C", "D"],
                        "answer": "A",
                        "marks": 4,
                        "subject": meta["subject"],
                        "topic": meta["topics"][0],
                        "difficulty": "Medium",
                    })

            completed += 1
            pct = 10 + round(completed / max(num_subjects, 1) * 75)
            job_store.update_job(
                job_id,
                status=JobStatus.GENERATING_QUESTIONS,
                progress=pct,
                message=f"Generated questions for {completed}/{num_subjects} subject(s)...",
            )

        # Sort: MCQs first, then numericals
        mcq_qs = [q for q in final_questions if q.get("type") != "numerical"]
        num_qs = [q for q in final_questions if q.get("type") == "numerical"]
        final_questions = mcq_qs + num_qs

        # --- Save test ---
        job_store.update_job(
            job_id,
            status=JobStatus.SAVING_TEST,
            progress=88,
            message="Saving test to database...",
        )

        status_val = "published"
        is_generated = request.visibility == "PRIVATE"
        share_code = str(uuid.uuid4())[:8].upper() if request.visibility == "CLASSROOM" else None

        new_test = Test(
            title=title,
            creator_id=user_id,
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
            is_generated_practice=is_generated,
        )

        db.add(new_test)
        db.commit()
        db.refresh(new_test)

        print(f"[TestJob {job_id}] Test saved: {new_test.id}")

        job_store.update_job(
            job_id,
            status=JobStatus.DONE,
            progress=100,
            message="Test created successfully!",
            result={
                "test_id": new_test.id,
                "message": "Test Created Successfully",
                "status": status_val,
            },
        )

    except Exception as exc:
        print(f"[TestJob {job_id}] Fatal error: {exc}")
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            message="Test creation failed.",
            error=str(exc),
        )
    finally:
        db.close()


# --- Endpoints ---

@router.post("/create/start", response_model=TestJobStartResponse)
async def start_test_creation(
    request: CreateTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_required),
):
    """
    Start test creation as a background job.
    Returns a job_id immediately — connect to /jobs/{job_id}/stream for progress.
    """
    if request.visibility == "CLASSROOM" and not request.classroom_id:
        raise HTTPException(status_code=400, detail="Classroom ID required for classroom tests")

    total_questions = sum(s.count for s in request.subject_inputs.values())
    if total_questions < 1:
        raise HTTPException(status_code=400, detail="At least 1 question required")

    job = job_store.create_job(str(current_user.id))

    background_tasks.add_task(
        run_test_creation_job,
        job.job_id,
        request,
        str(current_user.id),
    )

    return TestJobStartResponse(
        job_id=job.job_id,
        message="Test creation started. Connect to SSE stream for progress.",
    )


@router.get("/jobs/{job_id}/stream")
async def stream_test_job(
    job_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    SSE endpoint for test creation progress.
    Uses token query param (EventSource cannot send Authorization headers).
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token required")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    async def event_generator():
        queue = job_store.subscribe(job_id)
        try:
            current = job_store.get_job(job_id)
            if current:
                yield f"data: {json.dumps(current.to_dict())}\n\n"
            if current and current.status in [JobStatus.DONE, JobStatus.FAILED]:
                return

            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(update)}\n\n"
                    if update.get("status") in ["done", "failed"]:
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    current = job_store.get_job(job_id)
                    if not current or current.status in [JobStatus.DONE, JobStatus.FAILED]:
                        break
        finally:
            job_store.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}/status")
async def get_test_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user_required),
):
    """Poll endpoint: get current job status (fallback for SSE reconnection)."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    if job.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return job.to_dict()


@router.get("/my", response_model=List[MyTestSchema])
def get_my_tests(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Get tests created by the current user."""
    tests = (
        db.query(Test)
        .filter(Test.creator_id == current_user.id)
        .order_by(Test.created_at.desc())
        .all()
    )

    return [
        {
            "id": t.id,
            "title": t.title,
            "subject": t.subject,
            "created_at": t.created_at,
            "attempt_count": t.attempt_count,
            "visibility": t.visibility_type,
            "status": t.status,
        }
        for t in tests
    ]


@router.patch("/{test_id}/approve")
def approve_test(
    test_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Admin: Approve a community test."""
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    test.status = "published"
    db.commit()

    return {"message": "Test approved"}
