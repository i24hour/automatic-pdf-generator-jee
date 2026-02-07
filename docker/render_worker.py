"""
Render Worker - Listens to SQS and processes video generation jobs.
Run this on GPU-enabled EC2 instance.
"""

import os
import json
import asyncio
import time
import requests
import boto3
from manim_generator import ManimGenerator
from tts_engine import TTSEngine

# Configuration
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.infinitest.tech")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "infinitest-videos")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize AWS clients
sqs = boto3.client("sqs", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)

def update_job_status(job_id: str, status: str, progress: int, step: str, video_url: str = None, error: str = None):
    """
    Update job status via backend API.
    Note: Ideally we'd update DB directly or use a shared Redis, but calling API is simpler for decoupled worker.
    """
    try:
        # For now, we might need a dedicated internal API key or just use a shared secret
        # OR update via DB directly if worker has DB access
        # SIMPLIFICATION: printing for now, in production use shared DB or API callback
        print(f"JOB UPDATE [{job_id}]: {status} ({progress}%) - {step}")
        if error:
            print(f"ERROR: {error}")
        if video_url:
            print(f"VIDEO URL: {video_url}")
            
    except Exception as e:
        print(f"Failed to update status: {e}")

async def process_job(job_data):
    job_id = job_data["job_id"]
    print(f"Processing job: {job_id}")
    
    try:
        # 1. Generate Code
        update_job_status(job_id, "generating_code", 10, "Generating Manim code...")
        generator = ManimGenerator()
        code_result = await generator.generate_animation(
            topic=job_data["prompt"],
            language=job_data.get("language", "en"),
            max_duration=job_data.get("max_duration", 60)
        )
        
        if not code_result.get("success"):
            raise Exception(f"Code generation failed: {code_result.get('error')}")
            
        # 2. Render Video
        update_job_status(job_id, "rendering", 30, "Rendering animation...")
        render_result = await generator.render_video(code_result["manim_code"])
        
        if not render_result.get("success"):
            raise Exception(f"Rendering failed: {render_result.get('error')}")
            
        video_path = render_result["video_path"]
        
        # 3. Generate TTS
        update_job_status(job_id, "generating_audio", 70, "Generating audio...")
        tts = TTSEngine()
        full_narration = " ".join([s["text"] for s in code_result["narration_script"]])
        
        audio_result = await tts.generate_audio(
            text=full_narration,
            provider=job_data.get("tts_provider", "edge"),
            language=job_data.get("language", "en")
        )
        
        if not audio_result.get("success"):
            raise Exception(f"TTS failed: {audio_result.get('error')}")
            
        audio_path = audio_result["audio_path"]
        
        # 4. Combine (FFmpeg)
        update_job_status(job_id, "combining", 85, "Combining video and audio...")
        output_path = f"/tmp/{job_id}_final.mp4"
        cmd = f"ffmpeg -y -i {video_path} -i {audio_path} -c:v copy -c:a aac {output_path}"
        subprocess.run(cmd, shell=True, check=True)
        
        # 5. Upload to S3
        update_job_status(job_id, "uploading", 95, "Uploading to S3...")
        s3_key = f"videos/{job_id}.mp4"
        s3.upload_file(
            output_path, 
            S3_BUCKET_NAME, 
            s3_key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )
        
        video_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        update_job_status(job_id, "completed", 100, "Video ready!", video_url=video_url)
        
        # Cleanup
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)
        
    except Exception as e:
        update_job_status(job_id, "failed", 0, str(e), error=str(e))
        raise e

async def poll_queue():
    print(f"Worker listening on {SQS_QUEUE_URL}...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
            
            if "Messages" in response:
                message = response["Messages"][0]
                receipt_handle = message["ReceiptHandle"]
                body = json.loads(message["Body"])
                
                try:
                    await process_job(body)
                    # Delete message after successful processing
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                except Exception as e:
                    print(f"Job failed: {e}")
                    # Don't delete immediately, let visibility timeout handle retry (or move to DLQ)
            
        except Exception as e:
            print(f"Polling error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    if not SQS_QUEUE_URL:
        print("Error: SQS_QUEUE_URL not set")
        exit(1)
        
    asyncio.run(poll_queue())
