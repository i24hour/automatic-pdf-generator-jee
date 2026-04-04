from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from auth import get_current_user_required
from models import User, SupportTicket
from services.storage import storage

router = APIRouter(prefix="/support", tags=["Support"])

# ============================
# Schemas
# ============================

class TicketCreate(BaseModel):
    category: str
    description: str

class TicketResponse(BaseModel):
    id: str
    category: str
    description: str
    status: str
    attachment_url: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime
    admin_response: Optional[str] = None
    
    class Config:
        from_attributes = True

class TicketUpdate(BaseModel):
    status: str
    admin_response: Optional[str] = None

# ============================
# Configuration
# ============================

# TODO: Add your admin email here
ADMIN_EMAILS = ["admin@mentorsmantra.com", "mentorsmantra@gmail.com"] 

# ============================
# Endpoints
# ============================

@router.post("/create", response_model=TicketResponse)
async def create_ticket(
    category: str = Form(...),
    description: str = Form(...),
    screenshot: Optional[UploadFile] = File(None),
    voice_note: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Create a new support ticket with optional media."""
    
    attachment_url = None
    audio_url = None
    
    # Upload Screenshot if exists
    if screenshot:
        try:
            attachment_url = storage.upload_generic_file(
                screenshot.file, 
                screenshot.filename, 
                screenshot.content_type, 
                folder="tickets/screenshots"
            )
        except Exception as e:
            print(f"Screenshot upload failed: {e}")
            
    # Upload Voice Note if exists
    if voice_note:
        try:
            audio_url = storage.upload_generic_file(
                voice_note.file, 
                voice_note.filename, 
                voice_note.content_type, 
                folder="tickets/audio"
            )
        except Exception as e:
            print(f"Voice upload failed: {e}")

    ticket = SupportTicket(
        user_id=current_user.id,
        category=category,
        description=description,
        attachment_url=attachment_url,
        audio_url=audio_url
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

@router.get("/my", response_model=List[TicketResponse])
async def get_my_tickets(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get tickets for current user."""
    return db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id).order_by(SupportTicket.created_at.desc()).all()

# Admin Endpoints

@router.get("/admin/all", response_model=List[TicketResponse])
async def get_all_tickets(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Admin only: Get all tickets."""
    # Simple Admin Check
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return db.query(SupportTicket).order_by(SupportTicket.created_at.desc()).all()

@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: str,
    update: TicketUpdate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Admin only: Update ticket status."""
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket.status = update.status
    if update.admin_response:
        ticket.admin_response = update.admin_response
        
    db.commit()
    db.refresh(ticket)
    return ticket
