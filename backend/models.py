"""
Database models for User, Tokens, and PDF Generation tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, UniqueConstraint, Index
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
    is_premium = Column(Boolean, default=True)   # True for paid plans
    plan = Column(String, default="universe")         # "free" | "earth" | "universe"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pdf_generations = relationship("PDFGeneration", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    promo_usages = relationship("PromoCodeUsage", back_populates="user")
    shared_pdfs = relationship("SharedPDF", back_populates="user")
    pdf_likes = relationship("PDFLike", back_populates="user")
    pdf_likes = relationship("PDFLike", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    created_tests = relationship("Test", back_populates="creator")
    payment_orders = relationship("PaymentOrder", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("UserSubscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    @property
    def subscription_start(self):
        return self.subscription.starts_at if self.subscription else None

    @property
    def subscription_end(self):
        return self.subscription.expires_at if self.subscription else None
        
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

    is_institute = Column(Boolean, default=False, nullable=False, server_default="false")

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
    pdf_url = Column(String, nullable=False)  # S3 URL
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


# ============================================
# TEST PORTAL MODELS (NTA CBT-style)
# ============================================

class Test(Base):
    """
    A persistent, sharable test created by a user/AI.
    Acts as the 'Master' copy of the test.
    """
    __tablename__ = "tests"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False) # e.g., "Physics - Rotational Motion"
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Metadata
    subject = Column(String, nullable=False)
    topics_json = Column(Text, nullable=False) # JSON array of topics
    exam_type = Column(String, nullable=False) # JEE_MAINS, NEET
    difficulty = Column(String, nullable=False) # Easy, Medium, Hard
    
    # Stats
    total_questions = Column(Integer, nullable=False)
    total_marks = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    attempt_count = Column(Integer, default=0)
    
    # Content
    questions_data = Column(Text, nullable=False) # Full JSON of questions [{}, {}]
    
    # Visibility & Access Control (New Schema)
    # visibility_type: PRIVATE, CLASSROOM, COMMUNITY, ADMIN_CURATED
    visibility_type = Column(String, default="PRIVATE", index=True)
    
    # status: draft, pending_review, published, archived
    status = Column(String, default="published", index=True)
    
    classroom_id = Column(String, nullable=True, index=True)
    share_code = Column(String, unique=True, index=True, nullable=True)
    is_featured = Column(Boolean, default=False)
    is_generated_practice = Column(Boolean, default=False) # True for AI practice tests
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_tests")
    leaderboard_entries = relationship("TestLeaderboard", back_populates="test", cascade="all, delete-orphan")
    attempts = relationship("TestAttempt", back_populates="test")
    
    # Composite Index for efficient feed filtering
    __table_args__ = (
        Index('idx_test_visibility_status', 'visibility_type', 'status'),
    )

    def __repr__(self):
        return f"<Test {self.title} ({self.id})>"


class TestLeaderboard(Base):
    """
    Stores average/best performance of a user on a specific Test.
    Used for efficient leaderboard queries.
    """
    __tablename__ = "test_leaderboard"
    __table_args__ = (
        UniqueConstraint("test_id", "user_id", name="uq_test_leaderboard_user"),
    )
    
    id = Column(String, primary_key=True, default=generate_uuid)
    test_id = Column(String, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Best Performance Stats
    score = Column(Integer, nullable=False)
    time_taken_seconds = Column(Integer, nullable=False)
    accuracy = Column(Integer, nullable=False) # stored as percentage (0-100) or float
    
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    test = relationship("Test", back_populates="leaderboard_entries")
    user = relationship("User")
    
    def __repr__(self):
        return f"<Leaderboard Test={self.test_id} User={self.user_id} Score={self.score}>"


class TestAttempt(Base):
    """A user's test session - stores test configuration and results."""
    __tablename__ = "test_attempts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id = Column(String, ForeignKey("tests.id"), nullable=True, index=True) # Optional link to master test
    
    # Test Configuration
    exam_type = Column(String, nullable=False)  # JEE_MAINS, JEE_ADV, NEET, CUSTOM
    total_questions = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    topics_json = Column(Text, nullable=False)  # JSON array of topics
    subject_distribution_json = Column(Text, nullable=True)  # {"Physics": 25, "Chemistry": 25, "Maths": 25}
    difficulty_distribution_json = Column(Text, nullable=True)  # {"easy": 20, "medium": 50, "hard": 30}
    
    # State
    status = Column(String, default="NOT_STARTED")  # NOT_STARTED, IN_PROGRESS, SUBMITTED, EXPIRED
    current_question_index = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Results (populated after submission)
    total_score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    correct_count = Column(Integer, nullable=True)
    wrong_count = Column(Integer, nullable=True)
    unattempted_count = Column(Integer, nullable=True)
    
    # Relationships
    responses = relationship("QuestionResponse", back_populates="test_attempt", cascade="all, delete-orphan")
    user = relationship("User")
    test = relationship("Test", back_populates="attempts")
    
    def __repr__(self):
        return f"<TestAttempt {self.exam_type} for {self.user_id}>"


class QuestionResponse(Base):
    """Individual question in test with NTA 5-state response tracking."""
    __tablename__ = "question_responses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    test_attempt_id = Column(String, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_index = Column(Integer, nullable=False)  # 0-indexed position
    
    # Question Data (denormalized for performance)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)  # Easy, Medium, Hard
    question_type = Column(String, nullable=False)  # mcq, numerical
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)  # JSON: {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer = Column(String, nullable=False)
    solution = Column(Text, nullable=True)
    marks_correct = Column(Integer, default=4)
    marks_wrong = Column(Integer, default=-1)  # Negative marking
    diagram_json = Column(Text, nullable=True)  # JSON: { "diagram_type": "ray_optics", "elements": [...] }
    diagram_image_url = Column(String, nullable=True)  # S3 URL for extracted diagram images (PDF-to-Test)
    
    # User Response - NTA 5 States
    # NOT_VISITED, NOT_ANSWERED, ANSWERED, MARKED_REVIEW, ANSWERED_MARKED
    status = Column(String, default="NOT_VISITED")
    user_answer = Column(String, nullable=True)  # NULL = unattempted
    is_marked_for_review = Column(Boolean, default=False)
    time_spent_seconds = Column(Integer, default=0)
    last_visited_at = Column(DateTime(timezone=True), nullable=True)
    
    # Computed after submission
    is_correct = Column(Boolean, nullable=True)
    marks_obtained = Column(Integer, nullable=True)
    
    # Relationship
    test_attempt = relationship("TestAttempt", back_populates="responses")
    
    def __repr__(self):
        return f"<QuestionResponse Q{self.question_index} in {self.test_attempt_id}>"

class SupportTicket(Base):
    """Support ticket raised by user."""
    __tablename__ = "support_tickets"

    id = Column(String, primary_key=True, default=generate_uuid)
    # Use CASCADE to delete tickets if user is deleted.
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    category = Column(String, nullable=False) # Bug, Feature, Content, Other
    description = Column(Text, nullable=False)
    
    # Media Links
    attachment_url = Column(String, nullable=True) # Screenshot
    audio_url = Column(String, nullable=True)      # Voice Note
    
    # Status
    status = Column(String, default="OPEN") # OPEN, IN_PROGRESS, RESOLVED
    admin_response = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    user = relationship("User", back_populates="tickets")

# Update User relationship
User.tickets = relationship("SupportTicket", back_populates="user")


class APIUsageLog(Base):
    """Log individual LLM API calls for cost tracking and analytics."""
    __tablename__ = "api_usage_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    # user_id is nullable mostly for system calls or pre-login checks (if any)
    user_id = Column(String, nullable=True, index=True) 
    # generation_id links all per-call logs to a single test/pdf generation session
    generation_id = Column(String, nullable=True, index=True)
    feature = Column(String, nullable=False)  # e.g. "pdf_generator", "test_portal", "verify_numerical"
    model_name = Column(String, nullable=False)
    
    # Token Stats
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Context Metadata
    subject = Column(String, nullable=True)
    level = Column(String, nullable=True)    # JEE Mains, NEET, etc.
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<APILog {self.feature} - {self.total_tokens} tokens>"


class TotalAPIUsage(Base):
    """Per-generation summary: total tokens used across ALL LLM calls for one test/pdf."""
    __tablename__ = "total_api_usage"

    id = Column(String, primary_key=True, default=generate_uuid)
    generation_id = Column(String, unique=True, nullable=False, index=True)  # links to api_usage_logs.generation_id
    user_id = Column(String, nullable=True, index=True)
    
    # What was generated
    feature = Column(String, nullable=True)   # "pdf_generator", "test_portal", etc.
    subject = Column(String, nullable=True)
    level = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    
    # Aggregated Token Stats
    total_input_tokens = Column(Integer, nullable=False, default=0)
    total_output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # How many individual LLM calls were made
    api_call_count = Column(Integer, nullable=False, default=0)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<TotalAPIUsage gen={self.generation_id[:8]} tokens={self.total_tokens}>"


# ============================================================
# Payment & Subscription Models
# ============================================================

class PaymentOrder(Base):
    """Tracks every Cashfree payment order."""
    __tablename__ = "payment_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cf_order_id = Column(String, unique=True, index=True, nullable=False)
    cf_payment_id = Column(String, nullable=True)
    plan_key = Column(String, nullable=False)   # "earth_monthly" | "universe_monthly"
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, default="PENDING")  # PENDING | PAID | FAILED
    payment_session_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="payment_orders")

    def __repr__(self):
        return f"<PaymentOrder {self.cf_order_id} {self.status}>"


class UserSubscription(Base):
    """One row per user — upserted on each successful payment."""
    __tablename__ = "user_subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan = Column(String, default="free", nullable=False)  # "free" | "earth" | "universe"
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscription")

    def __repr__(self):
        return f"<UserSubscription {self.plan} expires={self.expires_at}>"


# ============================================================
# PDF to Test Feature Models
# ============================================================

class PDFExtractJob(Base):
    """Tracks a PDF upload → parsed questions → test creation workflow."""
    __tablename__ = "pdf_extract_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Uploaded PDF
    pdf_url = Column(String, nullable=False)
    pdf_filename = Column(String, nullable=False)

    # Workflow status
    status = Column(String, default="parsing")  # parsing, review, created, failed

    # Note: parsing progress is stored in extracted_questions_json as {"_progress": {"done": N, "total": M}}
    # while status == "parsing", to avoid needing new DB columns

    # Parsed data
    title = Column(String, nullable=True)
    duration_minutes = Column(Integer, default=180)
    exam_type = Column(String, default="JEE_MAINS")
    extracted_questions_json = Column(Text, nullable=True)  # JSON array of parsed questions + images
    answer_key_json = Column(Text, nullable=True)           # JSON map {question_number: answer}

    # Linked test once created
    test_id = Column(String, ForeignKey("tests.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user = relationship("User")
    test = relationship("Test")

    def __repr__(self):
        return f"<PDFExtractJob {self.id} status={self.status}>"


class ExtractedDiagramImage(Base):
    """Stores extracted images from a PDF with linkage to the extract job."""
    __tablename__ = "extracted_diagram_images"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("pdf_extract_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # S3 URL of the extracted PNG
    image_url = Column(String, nullable=False)

    # Page + bbox for traceability
    page_number = Column(Integer, nullable=False)
    bbox_json = Column(Text, nullable=True)  # {x0, y0, x1, y1}

    # Association (filled later by proximity logic)
    associated_question_number = Column(Integer, nullable=True)
    association_confidence = Column(String, default="medium")  # high, medium, low

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ExtractedDiagramImage job={self.job_id} page={self.page_number}>"
