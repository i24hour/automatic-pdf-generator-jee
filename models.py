"""
Database models for User, Tokens, and PDF Generation tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid
import secrets


def generate_uuid():
    return str(uuid.uuid4())


def generate_token():
    return secrets.token_urlsafe(32)


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    is_verified = Column(Boolean, default=False)
    total_posts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pdf_generations = relationship("PDFGeneration", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    shared_pdfs = relationship("SharedPDF", back_populates="user", cascade="all, delete-orphan")
    pdf_likes = relationship("PDFLike", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class RefreshToken(Base):
    """Refresh tokens for maintaining user sessions."""
    __tablename__ = "refresh_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True, nullable=False, default=generate_token)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<RefreshToken {self.id[:8]}...>"


class VerificationToken(Base):
    """Email verification tokens."""
    __tablename__ = "verification_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True, nullable=False, default=generate_token)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<VerificationToken {self.token[:8]}...>"


class PasswordResetToken(Base):
    """Password reset tokens."""
    __tablename__ = "password_reset_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True, nullable=False, default=generate_token)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<PasswordResetToken {self.token[:8]}...>"


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
    
    # Relationship
    user = relationship("User", back_populates="pdf_generations")
    
    def __repr__(self):
        return f"<PDFGeneration {self.topic} by {self.user_id}>"


class JobStatus(Base):
    """Track background job status for PDF generation."""
    __tablename__ = "job_statuses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)
    question_count = Column(Integer, nullable=False)
    pdf_filename = Column(String, nullable=True)
    pdf_data = Column(Text, nullable=True)  # Base64 encoded PDF for temporary storage
    error_message = Column(Text, nullable=True)
    progress = Column(Integer, default=0)  # 0-100 percent
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<JobStatus {self.id[:8]} - {self.status}>"


class TopicSubjectCache(Base):
    """Cache of detected subjects for topics to avoid repeated LLM calls."""
    __tablename__ = "topic_subject_cache"
    __table_args__ = (
        UniqueConstraint("normalized_topic", name="uq_topic_subject_cache_normalized"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    topic = Column(String, nullable=False)
    normalized_topic = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    confidence = Column(String, nullable=False, default="high")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TopicSubjectCache topic={self.normalized_topic} subject={self.subject}>"


class SharedPDF(Base):
    """Shared/Posted PDFs for community feed."""
    __tablename__ = "shared_pdfs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    pdf_url = Column(String, nullable=False)
    pdf_filename = Column(String, nullable=False)
    caption = Column(Text, nullable=True)

    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    question_count = Column(Integer, default=0)
    has_solutions = Column(Boolean, default=False)

    visibility = Column(String, default="private")
    slug = Column(String, unique=True, index=True, nullable=True)

    download_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="shared_pdfs")
    likes = relationship("PDFLike", back_populates="shared_pdf", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SharedPDF {self.topic} by {self.user_id}>"


class PDFLike(Base):
    """Track likes on shared PDFs."""
    __tablename__ = "pdf_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "shared_pdf_id", name="uq_user_pdf_like"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_pdf_id = Column(String, ForeignKey("shared_pdfs.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="pdf_likes")
    shared_pdf = relationship("SharedPDF", back_populates="likes")

    def __repr__(self):
        return f"<PDFLike user={self.user_id} pdf={self.shared_pdf_id}>"


class UserBadge(Base):
    """Badges earned by users."""
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_type", name="uq_user_badge"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_type = Column(String, nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="badges")

    def __repr__(self):
        return f"<UserBadge {self.badge_type} for {self.user_id}>"
