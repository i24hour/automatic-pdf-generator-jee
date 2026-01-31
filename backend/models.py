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
    username = Column(String, unique=True, index=True, nullable=True)  # Public display name
    phone = Column(String, nullable=True)  # Phone number
    class_grade = Column(String, nullable=True)  # Class/Grade (Optional)
    is_verified = Column(Boolean, default=False)
    bonus_limit = Column(Integer, default=0)  # Permanent extra limit
    monthly_bonus_limit = Column(Integer, default=0)  # Monthly extra limit (resets every month)
    last_bonus_month = Column(String, nullable=True)  # Track which month the monthly bonus belongs to (YYYY-MM)
    total_likes_received = Column(Integer, default=0)  # Cache for leaderboard
    total_posts = Column(Integer, default=0)  # Cache for leaderboard
    fresh_questions_enabled = Column(Boolean, default=True)  # Toggle for fresh questions feature
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pdf_generations = relationship("PDFGeneration", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    promo_usages = relationship("PromoCodeUsage", back_populates="user")
    shared_pdfs = relationship("SharedPDF", back_populates="user")
    pdf_likes = relationship("PDFLike", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    
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
    
    # Background Task Fields
    status = Column(String, default="COMPLETED")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    job_id = Column(String, nullable=True)  # For tracking
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="pdf_generations")
    
    def __repr__(self):
        return f"<PDFGeneration {self.topic} by {self.user_id}>"


class PromoCode(Base):
    """Promo codes for bonus generations."""
    __tablename__ = "promo_codes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, index=True, nullable=False)
    bonus_limit = Column(Integer, nullable=False, default=10)  # Extra generations
    max_uses = Column(Integer, nullable=False, default=2)  # Max users who can use
    current_uses = Column(Integer, default=0)  # How many times used
    is_active = Column(Boolean, default=True)
    is_monthly_only = Column(Boolean, default=False)  # If true, bonus applies only to current month
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration date
    
    # Relationships
    usages = relationship("PromoCodeUsage", back_populates="promo_code")
    
    def __repr__(self):
        return f"<PromoCode {self.code}>"


class PromoCodeUsage(Base):
    """Track which users have used which promo codes."""
    __tablename__ = "promo_code_usages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    promo_code_id = Column(String, ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="promo_usages")
    promo_code = relationship("PromoCode", back_populates="usages")
    
    def __repr__(self):
        return f"<PromoCodeUsage user={self.user_id} code={self.promo_code_id}>"


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


class InstituteUser(Base):
    """Institute user model for separate authentication."""
    __tablename__ = "institute_users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Profile info (shown on PDF)
    institute_name = Column(String, nullable=True)
    contact_number = Column(String, nullable=True)
    institute_email = Column(String, nullable=True)
    
    # Rate limiting (same as regular users)
    monthly_bonus_limit = Column(Integer, default=0)
    last_bonus_month = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generations = relationship("InstituteGeneration", back_populates="institute_user")
    refresh_tokens = relationship("InstituteRefreshToken", back_populates="institute_user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<InstituteUser {self.email}>"


class InstituteRefreshToken(Base):
    """Refresh tokens for institute user sessions."""
    __tablename__ = "institute_refresh_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True, nullable=False, default=generate_token)
    institute_user_id = Column(String, ForeignKey("institute_users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    institute_user = relationship("InstituteUser", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<InstituteRefreshToken {self.id[:8]}...>"


class InstituteGeneration(Base):
    """Track PDF generations by institute users."""
    __tablename__ = "institute_generations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    institute_user_id = Column(String, ForeignKey("institute_users.id", ondelete="CASCADE"), nullable=False)
    
    # Request details
    chapters = Column(Text, nullable=False)  # JSON array of chapters
    exam_type = Column(String, nullable=False)  # Mains, NEET, Advanced
    difficulty = Column(String, nullable=False)  # Easy, Medium, Hard
    physics_count = Column(Integer, default=0)
    chemistry_count = Column(Integer, default=0)
    maths_count = Column(Integer, default=0)
    biology_count = Column(Integer, default=0)  # For NEET (Zoology + Botany)
    
    # Output
    pdf_filename = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    institute_user = relationship("InstituteUser", back_populates="generations")
    
    def __repr__(self):
        return f"<InstituteGeneration {self.exam_type} by {self.institute_user_id}>"


class SharedPDF(Base):
    """Shared/Posted PDFs for community feed."""
    __tablename__ = "shared_pdfs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # PDF Info
    pdf_url = Column(String, nullable=False)  # Cloudflare R2 URL
    pdf_filename = Column(String, nullable=False)
    caption = Column(Text, nullable=True)  # User's post text
    
    # Metadata
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)  # JEE Mains, Advanced, NEET
    difficulty = Column(String, nullable=False)
    question_count = Column(Integer, default=0)
    has_solutions = Column(Boolean, default=False)
    
    # Visibility: public, unlisted, private
    visibility = Column(String, default="private")
    
    # Slug for unlisted access (e.g., /pdf/{slug})
    slug = Column(String, unique=True, index=True, nullable=True)
    
    # Engagement metrics
    download_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
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
    
    # Relationships
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
    badge_type = Column(String, nullable=False)  # first_post, prolific, popular, viral, etc.
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="badges")
    
    def __repr__(self):
        return f"<UserBadge {self.badge_type} for {self.user_id}>"


class SystemErrorLog(Base):
    """Log system errors (login failures, generation failures)."""
    __tablename__ = "system_error_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    error_type = Column(String, nullable=False)  # 'LOGIN_FAILURE', 'GENERATION_FAILURE', 'CLIENT_ERROR'
    error_details = Column(Text, nullable=False)  # JSON or text details
    user_id = Column(String, nullable=True)  # Optional: user ID if known
    user_email = Column(String, nullable=True)  # Optional: email used during attempt
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    metadata_info = Column(Text, nullable=True)  # JSON string for extra metadata (e.g. browser, IST time string)

    def __repr__(self):
        return f"<SystemErrorLog {self.error_type} at {self.timestamp}>"


class UserQuestionHistory(Base):
    """Store generated questions per user+topic+level for fresh question generation."""
    __tablename__ = "user_question_history"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", "level", "question_hash", name="uq_user_topic_question"),
    )
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String, nullable=False, index=True)
    level = Column(String, nullable=False)  # JEE, NEET, GATE, Boards
    question_text = Column(Text, nullable=False)
    question_hash = Column(String(32), nullable=False)  # MD5 hash for fast duplicate detection
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<UserQuestionHistory {self.topic} for {self.user_id}>"
