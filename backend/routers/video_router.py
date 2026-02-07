"""
Video Router - API endpoints for video generation.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import asyncio
import json

from database import get_db
from models import User
from routers.auth_router import get_current_user_info as get_current_user




router = APIRouter(prefix="/api/video", tags=["Video Generation"])


# In-memory job store (replace with Redis/DB in production)
video_jobs = {}


# --- Pydantic Models ---

class VideoGenerateRequest(BaseModel):
    """Request model for video generation."""
    prompt: str = Field(..., min_length=5, max_length=1000, description="Math topic or question")
    topic: str = Field(default="Geometry", description="Topic category")
    language: str = Field(default="en", description="Language code (en/hi)")
    tts_provider: str = Field(default="edge", description="TTS provider (edge/elevenlabs/openai)")
    max_duration: int = Field(default=60, ge=30, le=300, description="Max video duration in seconds")


class VideoJobStatus(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str  # pending, generating_code, rendering, generating_audio, combining, completed, failed
    progress: int  # 0-100
    current_step: str
    video_url: Optional[str] = None
    error: Optional[str] = None
    estimated_time_remaining: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime


class VideoInfo(BaseModel):
    """Response model for video info."""
    id: str
    title: str
    prompt: str
    topic: str
    language: str
    duration_seconds: Optional[int]
    video_url: str
    thumbnail_url: Optional[str]
    model_used: str
    tts_provider: str
    created_at: datetime


class TTSProviderInfo(BaseModel):
    """TTS provider info."""
    id: str
    name: str
    available: bool
    premium: bool = False


class VoiceInfo(BaseModel):
    """Voice info."""
    id: str
    name: str
    gender: str


# --- API Endpoints ---

@router.post("/generate")
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start video generation job.
    Returns job_id for tracking progress.
    """
    job_id = str(uuid.uuid4())
    
    # Create job entry
    video_jobs[job_id] = {
        "job_id": job_id,
        "user_id": current_user.id,
        "status": "pending",
        "progress": 0,
        "current_step": "Initializing...",
        "prompt": request.prompt,
        "topic": request.topic,
        "language": request.language,
        "tts_provider": request.tts_provider,
        "max_duration": request.max_duration,
        "video_url": None,
        "error": None,
        "model_used": None,
        "created_at": datetime.utcnow()
    }
    
    # Push job to SQS
    from services.aws_services import get_aws_services
    aws = get_aws_services()
    
    job_data = {
        "job_id": job_id,
        "prompt": request.prompt,
        "topic": request.topic,
        "language": request.language,
        "tts_provider": request.tts_provider,
        "max_duration": request.max_duration,
        "user_id": current_user.id
    }
    
    success = await aws.send_job_to_queue(job_data)
    
    if success:
        video_jobs[job_id]["status"] = "queued"
        video_jobs[job_id]["current_step"] = "Queued for processing..."
    else:
        video_jobs[job_id]["status"] = "failed"
        video_jobs[job_id]["error"] = "Failed to queue job"
    
    return {"job_id": job_id, "status": video_jobs[job_id]["status"]}


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get video generation job status."""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = video_jobs[job_id]
    
    # Security check
    if job["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return VideoJobStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        current_step=job["current_step"],
        video_url=job.get("video_url"),
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
    Stream job status updates using Server-Sent Events (SSE).
    """
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = video_jobs[job_id]
    
    if job["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    async def event_generator():
        last_progress = -1
        while True:
            if job_id not in video_jobs:
                break
                
            job = video_jobs[job_id]
            
            # Only send update if progress changed
            if job["progress"] != last_progress:
                last_progress = job["progress"]
                data = json.dumps({
                    "status": job["status"],
                    "progress": job["progress"],
                    "current_step": job["current_step"],
                    "video_url": job.get("video_url"),
                    "error": job.get("error")
                })
                yield f"data: {data}\n\n"
            
            # Stop if completed or failed
            if job["status"] in ["completed", "failed"]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/providers")
async def get_tts_providers():
    """Get available TTS providers."""
    tts = get_tts_engine()
    providers = tts.get_available_providers()
    return {"providers": providers}


@router.get("/voices")
async def get_voices(
    provider: str = Query(default="edge", description="TTS provider"),
    language: str = Query(default="en", description="Language code")
):
    """Get available voices for a provider and language."""
    tts = get_tts_engine()
    voices = tts.get_voices(provider, language)
    return {"voices": voices}


@router.get("/{video_id}")
async def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get video details."""
    # TODO: Implement with database
    if video_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = video_jobs[video_id]
    
    if job["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready")
    
    return VideoInfo(
        id=job["job_id"],
        title=job.get("title", job["prompt"][:50]),
        prompt=job["prompt"],
        topic=job["topic"],
        language=job["language"],
        duration_seconds=job.get("duration_seconds"),
        video_url=job["video_url"],
        thumbnail_url=None,
        model_used=job.get("model_used", "unknown"),
        tts_provider=job["tts_provider"],
        created_at=job["created_at"]
    )


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a video."""
    if video_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = video_jobs[video_id]
    
    if job["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # TODO: Delete from S3
    del video_jobs[video_id]
    
    return {"success": True, "message": "Video deleted"}


@router.get("/history/me")
async def get_my_videos(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get user's video generation history."""
    user_jobs = [
        job for job in video_jobs.values()
        if job["user_id"] == current_user.id and job["status"] == "completed"
    ]
    
    # Sort by created_at descending
    user_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    paginated = user_jobs[offset:offset + limit]
    
    return {
        "videos": paginated,
        "total": len(user_jobs),
        "limit": limit,
        "offset": offset
    }


# --- Background Task ---

async def process_video_generation(
    job_id: str,
    request: VideoGenerateRequest,
    user_id: str
):
    """
    Background task for video generation.
    Steps:
    1. Generate Manim code with LLM
    2. Validate code
    3. Render video with Manim
    4. Generate TTS audio
    5. Combine video + audio
    6. Upload to S3
    """
    job = video_jobs[job_id]
    
    try:
        # Step 1: Generate Manim code
        job["status"] = "generating_code"
        job["progress"] = 10
        job["current_step"] = "Generating animation code..."
        
        generator = get_manim_generator()
        code_result = await generator.generate_animation(
            topic=request.prompt,
            language=request.language,
            max_duration=request.max_duration
        )
        
        if not code_result.get("success"):
            raise Exception(f"Code generation failed: {code_result.get('error')}")
        
        job["model_used"] = code_result.get("model_used")
        job["title"] = code_result.get("title", request.prompt[:50])
        
        # Step 2: Validate code
        job["progress"] = 20
        job["current_step"] = "Validating animation code..."
        
        validation = generator.validate_code(code_result["manim_code"])
        if not validation.get("valid", False):
            raise Exception(f"Code validation failed: {validation.get('error')}")
        
        # Step 3: Render video (PLACEHOLDER - needs Docker setup)
        job["status"] = "rendering"
        job["progress"] = 30
        job["current_step"] = "Rendering video animations..."
        
        # TODO: Implement actual rendering with Docker/EC2
        # For now, simulate rendering
        await asyncio.sleep(5)
        job["progress"] = 60
        
        # Step 4: Generate TTS audio
        job["status"] = "generating_audio"
        job["progress"] = 70
        job["current_step"] = "Generating voice narration..."
        
        tts = get_tts_engine()
        
        # Combine all narration scripts
        full_narration = " ".join([
            segment["text"] for segment in code_result["narration_script"]
        ])
        
        audio_result = await tts.generate_audio(
            text=full_narration,
            provider=request.tts_provider,
            language=request.language
        )
        
        if not audio_result.get("success"):
            raise Exception(f"TTS failed: {audio_result.get('error')}")
        
        job["progress"] = 85
        
        # Step 5: Combine video + audio (PLACEHOLDER)
        job["status"] = "combining"
        job["progress"] = 90
        job["current_step"] = "Combining video and audio..."
        
        # TODO: Implement FFmpeg combining
        await asyncio.sleep(2)
        
        # Step 6: Upload to S3 (PLACEHOLDER)
        job["progress"] = 95
        job["current_step"] = "Uploading video..."
        
        # TODO: Implement S3 upload
        await asyncio.sleep(1)
        
        # Complete
        job["status"] = "completed"
        job["progress"] = 100
        job["current_step"] = "Video ready!"
        job["video_url"] = f"https://example.com/videos/{job_id}.mp4"  # Placeholder
        job["duration_seconds"] = code_result.get("estimated_duration", 60)
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_step"] = f"Failed: {str(e)}"
        print(f"Video generation failed for {job_id}: {e}")
