"""
Database models for User and PDF Generation tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to PDF generations
    pdf_generations = relationship("PDFGeneration", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"


class PDFGeneration(Base):
    """Track PDF generations for rate limiting."""
    __tablename__ = "pdf_generations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)
    question_count = Column(Integer, nullable=False)
    pdf_filename = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to user
    user = relationship("User", back_populates="pdf_generations")
    
    def __repr__(self):
        return f"<PDFGeneration {self.topic} by {self.user_id}>"
