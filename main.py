"""
Mentors Mantra Test Generator - FastAPI Backend
Main application entry point with API endpoints.
"""

import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from services.llm_engine import llm_engine
from services.pdf_engine import pdf_engine

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Mentors Mantra Test Generator",
    description="Generate professionally formatted PDF test papers using AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for test generation."""
    subject: str = Field(..., description="Subject: Physics, Chemistry, or Maths")
    topic: str = Field(..., description="Specific topic for the test")
    total_questions: int = Field(default=20, ge=5, le=50, description="Total number of questions")
    level: str = Field(default="JEE Mains", description="Difficulty level: Boards, JEE Mains, JEE Advanced, Olympiad")


class GenerateResponse(BaseModel):
    """Response model for successful generation."""
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    total_mcq: int = 0
    total_numerical: int = 0


class ErrorResponse(BaseModel):
    """Response model for errors."""
    success: bool = False
    error: str


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Mentors Mantra Test Generator",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "active_model": os.getenv("ACTIVE_MODEL", "not configured"),
        "services": {
            "llm_engine": "ready",
            "pdf_engine": "ready"
        }
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_test(request: GenerateRequest):
    """
    Generate a test paper PDF.
    
    - **subject**: The subject (Physics, Chemistry, Maths)
    - **topic**: The specific topic for questions
    - **total_questions**: Total number of questions (default: 20, range: 5-50)
    
    Returns a PDF file download.
    """
    try:
        # Calculate question split: 80% MCQ, 20% Numerical
        mcq_count = int(request.total_questions * 0.8)
        numerical_count = request.total_questions - mcq_count
        
        # Ensure at least 1 of each type
        if mcq_count < 1:
            mcq_count = 1
        if numerical_count < 1:
            numerical_count = 1
            mcq_count = request.total_questions - 1
        
        # Generate questions using LLM
        llm_result = llm_engine.generate_questions(
            subject=request.subject,
            topic=request.topic,
            mcq_count=mcq_count,
            numerical_count=numerical_count,
            level=request.level
        )
        
        if not llm_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=llm_result.get("error", "Failed to generate questions")
            )
        
        # Generate unique filename
        filename = f"test_{request.subject}_{request.topic}_{uuid.uuid4().hex[:8]}"
        filename = filename.replace(" ", "_").lower()
        
        # Generate PDF
        pdf_path = pdf_engine.generate_pdf(llm_result, filename)
        
        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF. Please check if pdflatex is installed."
            )
        
        return GenerateResponse(
            success=True,
            message="Test paper generated successfully",
            pdf_filename=os.path.basename(pdf_path),
            total_mcq=mcq_count,
            total_numerical=numerical_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def download_pdf(filename: str):
    """
    Download a generated PDF file.
    
    - **filename**: The PDF filename returned from /api/generate
    """
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    pdf_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf"
    )


@app.get("/api/models")
async def list_models():
    """List available LLM models."""
    return {
        "active_model": os.getenv("ACTIVE_MODEL", "gemini/gemini-1.5-flash"),
        "available_models": [
            "gemini/gemini-1.5-flash",
            "gemini/gemini-1.5-pro",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3-sonnet-20240229",
            "anthropic/claude-3-haiku-20240307"
        ]
    }


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
