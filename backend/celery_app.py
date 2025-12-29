"""
Celery configuration for background task processing.
Uses Redis as message broker and result backend.
"""

import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Ensure the app directory is in Python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

load_dotenv()

# Redis URL from Heroku or local
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Fix for Heroku Redis SSL
if REDIS_URL.startswith("rediss://"):
    REDIS_URL = REDIS_URL + "?ssl_cert_reqs=none"

# Create Celery app
celery_app = Celery(
    "mentors_mantra",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    result_expires=3600,  # Results expire after 1 hour
)
