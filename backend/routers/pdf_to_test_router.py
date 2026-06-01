"""
PDF to Test Router
Upload a JEE Mains PDF → extract questions + images → review → create Test
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, BackgroundTasks
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, Test, PDFExtractJob, ExtractedDiagramImage,
    generate_uuid
)
from auth import get_current_user_required
from services.storage import storage
from services.pdf_parser import pdf_parser, ParseResult

router = APIRouter(prefix="/api/pdf-to-test", tags=["PDF to Test"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UploadPDFResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ReviewQuestion(BaseModel):
    question_number: int
    text: str
    options: Dict[str, str]
    answer: Optional[str] = None
    type: str = "mcq"
    subject: str = "Physics"
    image_urls: List[str] = []


class ReviewDataResponse(BaseModel):
    job_id: str
    status: str
    title: str
    duration_minutes: int
    exam_type: str
    questions: List[ReviewQuestion]
    subjects: List[str]
    pages_total: Optional[int] = None
    pages_done: Optional[int] = None


class UpdateReviewRequest(BaseModel):
    questions: List[ReviewQuestion]
    title: Optional[str] = None
    duration_minutes: Optional[int] = None


class CreateTestFromPDFRequest(BaseModel):
    job_id: str
    visibility: str = "PRIVATE"  # PRIVATE, CLASSROOM, COMMUNITY
    classroom_id: Optional[str] = None


class CreateTestFromPDFResponse(BaseModel):
    test_id: str
    message: str
    redirect_url: str


# ---------------------------------------------------------------------------
# Helper: save extracted images to S3
# ---------------------------------------------------------------------------

def _save_extracted_images(
    job_id: str,
    parse_result: ParseResult,
    user_id: str,
    db: Session
) -> Dict[int, List[str]]:
    """
    Save extracted images to S3 and return mapping:
    {question_number: [image_url1, image_url2, ...]}
    """
    from services.pdf_parser import ExtractedImage

    qnum_to_urls: Dict[int, List[str]] = {}

    for idx, img in enumerate(parse_result.images):
        # Determine associated question by proximity
        best_qnum = None
        best_dist = float("inf")

        for q in parse_result.questions:
            if q.page_number != img.page_number:
                continue
            # Use stored bboxes if association happened
            for qb in q.image_bboxes:
                dy = abs(img.bbox[1] - qb[1])
                if dy < best_dist:
                    best_dist = dy
                    best_qnum = q.question_number

        # Save image to temp file and upload
        ext = img.ext if img.ext.startswith(".") else f".{img.ext}"
        tmp_filename = f"extract_{job_id}_p{img.page_number}_{idx}{ext}"
        tmp_path = f"/tmp/{tmp_filename}"

        try:
            with open(tmp_path, "wb") as f:
                f.write(img.image_bytes)

            if storage.is_configured():
                s3_key = f"pdf-extracts/{user_id}/{job_id}/img_{idx}.png"
                url = storage.upload_generic_file(
                    open(tmp_path, "rb"),
                    filename=f"img_{idx}.png",
                    content_type="image/png",
                    folder="pdf-extracts",
                )
                if url:
                    # Record in DB
                    db_img = ExtractedDiagramImage(
                        job_id=job_id,
                        image_url=url,
                        page_number=img.page_number,
                        bbox_json=json.dumps(img.bbox),
                        associated_question_number=best_qnum,
                        association_confidence="high" if best_dist < 200 else "medium",
                    )
                    db.add(db_img)

                    if best_qnum is not None:
                        qnum_to_urls.setdefault(best_qnum, []).append(url)
        except Exception as e:
            print(f"[PDFToTest] Failed to save image {idx}: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    db.commit()
    return qnum_to_urls


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadPDFResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    title: str = Form("JEE Mains Practice"),
    duration_minutes: int = Form(180),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Upload a JEE Mains PDF. Extracts questions + images in the background.
    Returns a job_id. Poll GET /api/pdf-to-test/{job_id}/review to see results.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Save uploaded file to temp
    job_id = generate_uuid()
    tmp_pdf_path = f"/tmp/{job_id}.pdf"
    try:
        contents = await file.read()
        with open(tmp_pdf_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    # Upload original PDF to S3 for reference
    pdf_url = None
    if storage.is_configured():
        try:
            pdf_url = storage.upload_generic_file(
                open(tmp_pdf_path, "rb"),
                filename=f"{job_id}.pdf",
                content_type="application/pdf",
                folder="pdf-uploads",
            )
        except Exception as e:
            print(f"[PDFToTest] S3 upload of original PDF failed: {e}")

    # Create job record
    job = PDFExtractJob(
        id=job_id,
        user_id=current_user.id,
        pdf_url=pdf_url or f"local://{tmp_pdf_path}",
        pdf_filename=file.filename,
        status="parsing",
        title=title,
        duration_minutes=duration_minutes,
        exam_type="JEE_MAINS",
    )
    db.add(job)
    db.commit()

    # Trigger background parsing
    background_tasks.add_task(
        _run_pdf_parse_job,
        job_id=job_id,
        user_id=str(current_user.id),
        tmp_pdf_path=tmp_pdf_path,
        title=title,
        duration_minutes=duration_minutes,
    )

    return UploadPDFResponse(
        job_id=job_id,
        status="parsing",
        message="PDF uploaded successfully. Parsing in progress..."
    )

def _run_pdf_parse_job(
    job_id: str,
    user_id: str,
    tmp_pdf_path: str,
    title: str,
    duration_minutes: int,
):
    """Background task: parse PDF with Gemini Vision and store extracted data."""
    from database import SessionLocal

    db = SessionLocal()
    job = None
    try:
        job = db.query(PDFExtractJob).filter(PDFExtractJob.id == job_id).first()
        if not job:
            return

        # Progress callback — stores progress inside extracted_questions_json
        # (avoids needing new DB columns; safe for existing schema)
        def on_page_done(done: int, total: int):
            try:
                j = db.query(PDFExtractJob).filter(PDFExtractJob.id == job_id).first()
                if j:
                    j.extracted_questions_json = json.dumps(
                        {"_progress": {"done": done, "total": total}}
                    )
                    db.commit()
            except Exception as pe:
                print(f"[PDFToTest] Progress update error: {pe}")
                db.rollback()

        # Parse PDF with Gemini Vision
        result = pdf_parser.parse(
            tmp_pdf_path,
            title=title,
            duration_minutes=duration_minutes,
            progress_callback=on_page_done,
        )

        # Save extracted embedded images to S3
        qnum_to_urls = _save_extracted_images(job_id, result, user_id, db)

        # Apply image URLs to questions
        for q in result.questions:
            if q.question_number in qnum_to_urls:
                q.image_urls = qnum_to_urls[q.question_number]

        # Serialize to JSON (replaces the _progress placeholder with real questions)
        questions_json = pdf_parser.to_json(result)
        answer_key_json = {str(k): v for k, v in result.answer_key.items()}

        job.extracted_questions_json = json.dumps(questions_json)
        job.answer_key_json = json.dumps(answer_key_json)
        job.status = "review"
        db.commit()

        print(f"[PDFToTest] Job {job_id} complete: {len(result.questions)} questions, {len(result.images)} images")

    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        print(f"[PDFToTest] Parse job {job_id} FAILED: {e}")
        print(err_str)
        if job:
            job.status = "failed"
            try:
                job.extracted_questions_json = json.dumps({"error": str(e), "traceback": err_str[:500]})
            except Exception:
                pass
            db.commit()
    finally:
        db.close()
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)


@router.get("/{job_id}/review", response_model=ReviewDataResponse)
async def get_review_data(
    job_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Get parsed questions + images for review before creating the test."""
    job = db.query(PDFExtractJob).filter(
        PDFExtractJob.id == job_id,
        PDFExtractJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        if job.status == "parsing":
            # Read progress from extracted_questions_json if available
            pages_done = 0
            pages_total = None
            if job.extracted_questions_json:
                try:
                    prog_data = json.loads(job.extracted_questions_json)
                    if isinstance(prog_data, dict) and "_progress" in prog_data:
                        pages_done = prog_data["_progress"].get("done", 0)
                        pages_total = prog_data["_progress"].get("total")
                except Exception:
                    pass
            return ReviewDataResponse(
                job_id=job_id,
                status="parsing",
                title=job.title or "",
                duration_minutes=job.duration_minutes or 180,
                exam_type=job.exam_type,
                questions=[],
                subjects=[],
                pages_total=pages_total,
                pages_done=pages_done,
            )

        if job.status == "failed":
            error_detail = "PDF parsing failed. Please try again."
            if job.extracted_questions_json:
                try:
                    stored = json.loads(job.extracted_questions_json)
                    if isinstance(stored, dict) and "error" in stored:
                        error_detail = f"Parsing failed: {stored['error'][:200]}"
                except Exception:
                    pass
            raise HTTPException(status_code=400, detail=error_detail)

        # Deserialize questions
        questions = json.loads(job.extracted_questions_json or "[]")
        # If stored as dict (progress/error format), treat as empty
        if isinstance(questions, dict):
            questions = []
        subjects = list({q.get("subject", "Physics") for q in questions if isinstance(q, dict)})

        review_questions = [
            ReviewQuestion(
                question_number=q.get("question_number", i + 1),
                text=q.get("text", ""),
                options=q.get("options", {}),
                answer=q.get("answer"),
                type=q.get("type", "mcq"),
                subject=q.get("subject", "Physics"),
                image_urls=q.get("image_urls", []),
            )
            for i, q in enumerate(questions)
            if isinstance(q, dict)
        ]

        return ReviewDataResponse(
            job_id=job_id,
            status=job.status,
            title=job.title or "",
            duration_minutes=job.duration_minutes or 180,
            exam_type=job.exam_type,
            questions=review_questions,
            subjects=subjects,
            pages_total=None,
            pages_done=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[PDFToTest] get_review_data error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)[:200]}")


@router.put("/{job_id}/review", response_model=ReviewDataResponse)
async def update_review(
    job_id: str,
    request: UpdateReviewRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Save user edits from the review screen."""
    job = db.query(PDFExtractJob).filter(
        PDFExtractJob.id == job_id,
        PDFExtractJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("review", "created"):
        raise HTTPException(status_code=400, detail="Job is not in review state")

    # Update fields
    if request.title:
        job.title = request.title
    if request.duration_minutes:
        job.duration_minutes = request.duration_minutes

    # Serialize edited questions back
    edited = [
        {
            "question_number": q.question_number,
            "text": q.text,
            "options": q.options,
            "answer": q.answer,
            "type": q.type,
            "subject": q.subject,
            "image_urls": q.image_urls,
        }
        for q in request.questions
    ]
    job.extracted_questions_json = json.dumps(edited)
    db.commit()

    return ReviewDataResponse(
        job_id=job_id,
        status=job.status,
        title=job.title,
        duration_minutes=job.duration_minutes,
        exam_type=job.exam_type,
        questions=request.questions,
        subjects=list({q.subject for q in request.questions}),
    )


@router.post("/create-test", response_model=CreateTestFromPDFResponse)
async def create_test_from_pdf(
    request: CreateTestFromPDFRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Finalize reviewed questions and create a Test.
    Uses the existing Test model + TestAttempt flow.
    """
    job = db.query(PDFExtractJob).filter(
        PDFExtractJob.id == request.job_id,
        PDFExtractJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("review", "created"):
        raise HTTPException(status_code=400, detail="Job must be in review state")

    questions_data = json.loads(job.extracted_questions_json or "[]")
    if not questions_data:
        raise HTTPException(status_code=400, detail="No questions found in this PDF")

    # Build Test.questions_data format (array of dicts)
    final_questions = []
    subject_counts = {}

    for q in questions_data:
        subject = q.get("subject", "Physics")
        subject_counts[subject] = subject_counts.get(subject, 0) + 1

        final_questions.append({
            "text": q.get("text", ""),
            "question_text": q.get("text", ""),
            "options": q.get("options", {}),
            "answer": q.get("answer", "A"),
            "type": q.get("type", "mcq"),
            "subject": subject,
            "topic": subject,
            "difficulty": "Medium",
            "marks": 4,
            "diagram_image_url": q.get("image_urls", [None])[0],  # Primary image
            "image_urls": q.get("image_urls", []),
        })

    # Determine status based on visibility
    status_val = "published"
    share_code = None
    if request.visibility == "CLASSROOM":
        if not request.classroom_id:
            raise HTTPException(status_code=400, detail="Classroom ID required")
        share_code = str(uuid.uuid4())[:8].upper()

    # Create Test
    new_test = Test(
        title=job.title or "JEE Mains PDF Test",
        creator_id=current_user.id,
        subject=", ".join(subject_counts.keys()),
        topics_json=json.dumps(list(subject_counts.keys())),
        exam_type=job.exam_type,
        difficulty="Mixed",
        total_questions=len(final_questions),
        total_marks=sum(q.get("marks", 4) for q in final_questions),
        duration_minutes=job.duration_minutes or 180,
        questions_data=json.dumps(final_questions),
        visibility_type=request.visibility,
        status=status_val,
        classroom_id=request.classroom_id,
        share_code=share_code,
        is_generated_practice=False,
    )

    db.add(new_test)
    db.commit()
    db.refresh(new_test)

    # Link job to test
    job.test_id = new_test.id
    job.status = "created"
    db.commit()

    return CreateTestFromPDFResponse(
        test_id=new_test.id,
        message="Test created successfully from PDF",
        redirect_url=f"/test/{new_test.id}/instructions"
    )
