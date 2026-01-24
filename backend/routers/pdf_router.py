"""
PDF Router: Endpoints for PDF access including slug-based unlisted PDF access.
"""

import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, SharedPDF, generate_uuid
from auth import get_current_user_required, get_current_user
from services.gcs_storage import gcs_storage

router = APIRouter(prefix="/pdf", tags=["PDF"])


def generate_short_slug() -> str:
    """Generate a short unique slug for PDF sharing."""
    return secrets.token_urlsafe(8)  # 11 characters, URL-safe


class GenerateLinkResponse(BaseModel):
    """Response for generate link endpoint."""
    success: bool
    slug: str
    link: str


class PDFInfoResponse(BaseModel):
    """PDF information for public viewing."""
    id: str
    topic: str
    subject: str
    level: str
    difficulty: str
    question_count: int
    has_solutions: bool
    visibility: str
    download_url: Optional[str] = None


@router.get("/{slug}")
async def get_pdf_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Access a PDF by its slug. 
    - For public/unlisted PDFs: Returns a signed URL redirect
    - For private PDFs: Returns 404 (only owner can access)
    """
    pdf = db.query(SharedPDF).filter(SharedPDF.slug == slug).first()
    
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    # Private PDFs cannot be accessed via slug
    if pdf.visibility == "private":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    # Increment view count
    pdf.view_count = (pdf.view_count or 0) + 1
    db.commit()
    
    # Generate a signed URL (1 hour expiry) and redirect
    try:
        # Extract the blob name from the GCS URL
        # URL format: https://storage.googleapis.com/bucket-name/path/to/file.pdf
        # or gs://bucket-name/path/to/file.pdf
        pdf_url = pdf.pdf_url
        
        if pdf_url.startswith("gs://"):
            blob_name = pdf_url.split("/", 3)[-1]
        elif "storage.googleapis.com" in pdf_url:
            # Extract path after bucket name
            parts = pdf_url.split("/")
            bucket_idx = parts.index("storage.googleapis.com") + 2  # Skip protocol and bucket
            blob_name = "/".join(parts[bucket_idx:])
        else:
            # For R2 or other URLs, just redirect to the original URL
            return RedirectResponse(url=pdf_url, status_code=302)
        
        signed_url = gcs_storage.get_signed_url(blob_name, expiration_minutes=60)
        return RedirectResponse(url=signed_url, status_code=302)
        
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        # Fallback to original URL
        return RedirectResponse(url=pdf.pdf_url, status_code=302)


@router.get("/{slug}/info")
async def get_pdf_info(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get PDF metadata without downloading."""
    pdf = db.query(SharedPDF).filter(SharedPDF.slug == slug).first()
    
    if not pdf or pdf.visibility == "private":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    return {
        "success": True,
        "pdf": {
            "id": pdf.id,
            "topic": pdf.topic,
            "subject": pdf.subject,
            "level": pdf.level,
            "difficulty": pdf.difficulty,
            "question_count": pdf.question_count,
            "has_solutions": pdf.has_solutions,
            "visibility": pdf.visibility,
            "download_count": pdf.download_count,
            "like_count": pdf.like_count,
            "view_count": pdf.view_count,
            "created_at": pdf.created_at.isoformat() if pdf.created_at else None
        }
    }


@router.post("/{pdf_id}/generate-link")
async def generate_unlisted_link(
    pdf_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Generate a shareable link (slug) for a PDF.
    Only the owner can generate links for their PDFs.
    If a slug already exists, return the existing link.
    """
    pdf = db.query(SharedPDF).filter(
        SharedPDF.id == pdf_id,
        SharedPDF.user_id == current_user.id
    ).first()
    
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found or you don't have permission"
        )
    
    # Generate slug if not exists
    if not pdf.slug:
        pdf.slug = generate_short_slug()
        db.commit()
    
    return {
        "success": True,
        "slug": pdf.slug,
        "link": f"https://infinitest.tech/pdf/{pdf.slug}"
    }


@router.put("/{pdf_id}/visibility")
async def update_pdf_visibility(
    pdf_id: str,
    visibility: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Update PDF visibility (public, unlisted, private)."""
    if visibility not in ["public", "unlisted", "private"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid visibility. Must be 'public', 'unlisted', or 'private'"
        )
    
    pdf = db.query(SharedPDF).filter(
        SharedPDF.id == pdf_id,
        SharedPDF.user_id == current_user.id
    ).first()
    
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found or you don't have permission"
        )
    
    # Generate slug if setting to unlisted and no slug exists
    if visibility == "unlisted" and not pdf.slug:
        pdf.slug = generate_short_slug()
    
    pdf.visibility = visibility
    db.commit()
    
    return {
        "success": True,
        "visibility": visibility,
        "slug": pdf.slug if visibility == "unlisted" else None,
        "link": f"https://infinitest.tech/pdf/{pdf.slug}" if pdf.slug else None
    }
