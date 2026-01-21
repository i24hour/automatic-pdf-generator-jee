"""
Job Store Service
Tracks PDF generation jobs for SSE-based progress updates.
Jobs are stored in memory with automatic cleanup.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
import threading


class JobStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING_MCQS = "generating_mcqs"
    GENERATING_NUMERICALS = "generating_numericals"
    VERIFYING = "verifying"
    COMPILING_PDF = "compiling_pdf"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"


@dataclass
class GenerationJob:
    """Represents a PDF generation job."""
    job_id: str
    user_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100
    message: str = "Starting..."
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class JobStore:
    """Thread-safe in-memory job store with automatic cleanup."""
    
    def __init__(self, max_age_hours: int = 2):
        self._jobs: Dict[str, GenerationJob] = {}
        self._lock = threading.Lock()
        self._max_age = timedelta(hours=max_age_hours)
        self._subscribers: Dict[str, list] = {}  # job_id -> list of asyncio.Queue
    
    def create_job(self, user_id: str) -> GenerationJob:
        """Create a new job and return it."""
        job_id = str(uuid.uuid4())
        job = GenerationJob(job_id=job_id, user_id=user_id)
        
        with self._lock:
            self._jobs[job_id] = job
            self._subscribers[job_id] = []
        
        # Trigger cleanup of old jobs
        self._cleanup_old_jobs()
        
        print(f"[JobStore] Created job {job_id} for user {user_id}")
        return job
    
    def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[GenerationJob]:
        """Update a job and notify all subscribers."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if message is not None:
                job.message = message
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            
            job.updated_at = datetime.now(timezone.utc)
            
            # Notify subscribers
            self._notify_subscribers(job_id, job)
            
            print(f"[JobStore] Updated job {job_id}: {job.status.value} - {job.progress}%")
            return job
    
    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Subscribe to job updates. Returns an asyncio Queue."""
        queue = asyncio.Queue()
        with self._lock:
            if job_id in self._subscribers:
                self._subscribers[job_id].append(queue)
        return queue
    
    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        """Unsubscribe from job updates."""
        with self._lock:
            if job_id in self._subscribers:
                try:
                    self._subscribers[job_id].remove(queue)
                except ValueError:
                    pass
    
    def _notify_subscribers(self, job_id: str, job: GenerationJob):
        """Notify all subscribers of a job update."""
        if job_id not in self._subscribers:
            return
        
        for queue in self._subscribers[job_id]:
            try:
                queue.put_nowait(job.to_dict())
            except asyncio.QueueFull:
                pass
    
    def _cleanup_old_jobs(self):
        """Remove jobs older than max_age."""
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [
                job_id for job_id, job in self._jobs.items()
                if now - job.created_at > self._max_age
            ]
            for job_id in expired:
                del self._jobs[job_id]
                if job_id in self._subscribers:
                    del self._subscribers[job_id]
                print(f"[JobStore] Cleaned up expired job {job_id}")


# Singleton instance
job_store = JobStore()
