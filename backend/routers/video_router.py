"""
Video Router - API endpoints for video generation.

Pipeline (direct, no SQS):
  1. LLM generates Manim code + narration script
  2. Manim renders animation to .mp4 (subprocess)
  3. edge-tts generates audio narration to .mp3
  4. FFmpeg merges video + audio
  5. Uploads final .mp4 to GCS
  6. Frontend polls /status/{job_id} via SSE
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import asyncio
import json
import os
import tempfile
import subprocess

from database import get_db
from models import User
from auth import get_current_user_required as get_current_user
from services.tts_engine import get_tts_engine
from services.manim_generator import get_manim_generator
from services.gcs_storage import gcs_storage


router = APIRouter(prefix="/api/video", tags=["Video Generation"])


# In-memory job store (sufficient for Cloud Run's single instance mode)
# For multi-instance deploys, replace with Redis or DB
video_jobs: dict = {}


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=1000)
    topic: str = Field(default="Geometry")
    language: str = Field(default="en")
    tts_provider: str = Field(default="edge")
    max_duration: int = Field(default=60, ge=30, le=300)


class VideoJobStatus(BaseModel):
    job_id: str
    status: str   # pending | generating_code | rendering | generating_audio | combining | uploading | completed | failed
    progress: int
    current_step: str
    video_url: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    model_used: Optional[str] = None
    created_at: datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _update_job(job_id: str, **kwargs):
    """Safely update job fields."""
    if job_id in video_jobs:
        video_jobs[job_id].update(kwargs)


# ─── Background Pipeline ───────────────────────────────────────────────────────

async def process_video_generation(job_id: str, request: VideoGenerateRequest, user_id: str):
    """
    Full video generation pipeline running as a FastAPI background task with a global timeout.
    """
    try:
        # Enforce a strict 10-minute time limit for the entire process (prevents infinite hanging)
        await asyncio.wait_for(
            _run_video_pipeline(job_id, request, user_id),
            timeout=600
        )
    except asyncio.TimeoutError:
        _update_job(job_id, status="failed", error="Video generation timed out after 10 minutes.", current_step="Failed: Timeout exceeded")
        print(f"✗ Video job {job_id} timed out after 10 minutes")

async def _run_video_pipeline(job_id: str, request: VideoGenerateRequest, user_id: str):
    """Actual pipeline logic"""
    job = video_jobs[job_id]

    try:
        # ── Step 1: Generate Manim code via LLM ──────────────────────────────
        _update_job(job_id, status="generating_code", progress=10,
                    current_step="Generating animation code with AI...")

        generator = get_manim_generator()
        code_result = await generator.generate_animation(
            topic=request.prompt,
            language=request.language,
            max_duration=request.max_duration
        )

        if not code_result.get("success"):
            raise Exception(f"Code generation failed: {code_result.get('error')}")

        _update_job(job_id,
                    model_used=code_result.get("model_used"),
                    title=code_result.get("title", request.prompt[:50]))

        manim_code = code_result["manim_code"]
        narration_script = code_result.get("narration_script", [])

        # ── Step 2: Validate & auto-fix code syntax ──────────────────────────
        _update_job(job_id, progress=20, current_step="Validating animation code...")

        validation = generator.validate_code(manim_code)
        if validation.get("valid", False):
            # Use the (possibly auto-fixed) code
            manim_code = validation.get("code", manim_code)
        else:
            # Validation failed even after auto-fix — log and proceed anyway
            # (the render step will give the real error if code is truly broken)
            print(f"⚠ Code validation warning (proceeding to render): {validation.get('error')}")

        # ── Step 3: Render Manim video ────────────────────────────────────────
        _update_job(job_id, status="rendering", progress=30,
                    current_step="Rendering mathematical animation (this takes 1-3 mins)...")

        work_dir = tempfile.mkdtemp(prefix=f"video_{job_id}_")
        render_result = await generator.render_video(
            code=manim_code,
            output_dir=work_dir,
            quality="low"   # 480p for faster rendering on Cloud Run
        )

        if not render_result.get("success"):
            raise Exception(f"Manim render failed: {render_result.get('error')}")

        video_path = render_result["video_path"]
        _update_job(job_id, progress=60, current_step="Animation rendered successfully!")

        # ── Step 4: Generate TTS narration ───────────────────────────────────
        _update_job(job_id, status="generating_audio", progress=65,
                    current_step="Generating voice narration...")

        tts = get_tts_engine()

        full_narration = " ".join([
            seg["text"] for seg in narration_script
        ]) if narration_script else request.prompt

        audio_result = await tts.generate_audio(
            text=full_narration,
            provider=request.tts_provider,
            language=request.language
        )

        _update_job(job_id, progress=75, current_step="Voice narration generated!")

        # ── Step 5: Merge video + audio via FFmpeg ────────────────────────────
        _update_job(job_id, status="combining", progress=80,
                    current_step="Combining video and audio...")

        final_video_path = os.path.join(work_dir, "final_output.mp4")

        if audio_result.get("success") and audio_result.get("audio_path"):
            audio_path = audio_result["audio_path"]
            # Mix: loop video if shorter than audio, truncate at shorter of the two
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                final_video_path
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                if proc.returncode != 0:
                    print(f"FFmpeg warning (using silent video): {stderr.decode()[:500]}")
                    final_video_path = video_path  # fallback: silent video
            except (asyncio.TimeoutError, FileNotFoundError):
                print("FFmpeg unavailable or timed out — using silent video.")
                final_video_path = video_path
        else:
            # No audio — serve silent video
            final_video_path = video_path

        _update_job(job_id, progress=90, current_step="Video assembled!")

        # ── Step 6: Upload to GCS ─────────────────────────────────────────────
        _update_job(job_id, status="uploading", progress=92,
                    current_step="Uploading video to cloud storage...")

        video_url = None
        if gcs_storage.is_configured():
            object_key = f"videos/{user_id}/{job_id}.mp4"
            video_url = await asyncio.to_thread(
                gcs_storage.upload_video,
                final_video_path,
                object_key
            )

        if not video_url:
            # Fallback: serve from local static directory
            static_dir = os.path.join(os.path.dirname(__file__), "..", "static", "videos")
            os.makedirs(static_dir, exist_ok=True)
            local_name = f"{job_id}.mp4"
            local_path = os.path.join(static_dir, local_name)
            import shutil
            shutil.copy2(final_video_path, local_path)
            video_url = f"/static/videos/{local_name}"

        # ── Done ──────────────────────────────────────────────────────────────
        _update_job(job_id,
                    status="completed",
                    progress=100,
                    current_step="Video ready!",
                    video_url=video_url,
                    title=code_result.get("title", request.prompt[:50]),
                    duration_seconds=code_result.get("estimated_duration", 60))

        print(f"✓ Video job {job_id} completed: {video_url}")

    except Exception as e:
        _update_job(job_id,
                    status="failed",
                    error=str(e),
                    current_step=f"Failed: {str(e)[:200]}")
        print(f"✗ Video job {job_id} failed: {e}")

    finally:
        # Clean up temp dir
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


# ─── API Endpoints ─────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a video generation job. Returns job_id for status polling.
    Processing happens as a FastAPI background task (no SQS needed).
    """
    job_id = str(uuid.uuid4())

    video_jobs[job_id] = {
        "job_id": job_id,
        "user_id": current_user.id,
        "status": "pending",
        "progress": 0,
        "current_step": "Queued — starting shortly...",
        "prompt": request.prompt,
        "topic": request.topic,
        "language": request.language,
        "tts_provider": request.tts_provider,
        "max_duration": request.max_duration,
        "video_url": None,
        "title": None,
        "error": None,
        "model_used": None,
        "created_at": datetime.utcnow()
    }

    # Launch the pipeline as a non-blocking background task
    background_tasks.add_task(
        process_video_generation,
        job_id,
        request,
        current_user.id
    )

    return {"job_id": job_id, "status": "pending"}


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Poll video generation job status."""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = video_jobs[job_id]

    if job["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return VideoJobStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        current_step=job["current_step"],
        video_url=job.get("video_url"),
        title=job.get("title"),
        error=job.get("error"),
        model_used=job.get("model_used"),
        created_at=job["created_at"]
    )


@router.get("/status/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stream live status updates as Server-Sent Events (SSE).
    Frontend can use EventSource for real-time progress.
    """
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if video_jobs[job_id]["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    async def event_generator():
        last_progress = -1
        for _ in range(360):  # max 6 min (1s poll)
            if job_id not in video_jobs:
                break

            job = video_jobs[job_id]

            if job["progress"] != last_progress:
                last_progress = job["progress"]
                payload = json.dumps({
                    "status": job["status"],
                    "progress": job["progress"],
                    "current_step": job["current_step"],
                    "video_url": job.get("video_url"),
                    "error": job.get("error")
                })
                yield f"data: {payload}\n\n"

            if job["status"] in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/providers")
async def get_tts_providers():
    """Get available TTS providers."""
    tts = get_tts_engine()
    return {"providers": tts.get_available_providers()}


@router.get("/voices")
async def get_voices(
    provider: str = Query(default="edge"),
    language: str = Query(default="en")
):
    """Get available voices for a TTS provider."""
    tts = get_tts_engine()
    return {"voices": tts.get_voices(provider, language)}


@router.get("/history/me")
async def get_my_videos(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get video generation history for current user."""
    user_jobs = [
        job for job in video_jobs.values()
        if job["user_id"] == current_user.id and job["status"] == "completed"
    ]
    user_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    paginated = user_jobs[offset:offset + limit]

    return {"videos": paginated, "total": len(user_jobs), "limit": limit, "offset": offset}


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a video job."""
    if video_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Video not found")

    if video_jobs[video_id]["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    del video_jobs[video_id]
    return {"success": True}
