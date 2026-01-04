"""
Database models for User, Tokens, and PDF Generation tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
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
    phone = Column(String, nullable=True)  # Phone number
    is_verified = Column(Boolean, default=False)
    bonus_limit = Column(Integer, default=0)  # Extra limit from promo codes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pdf_generations = relationship("PDFGeneration", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    promo_usages = relationship("PromoCodeUsage", back_populates="user")
    
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


class PromoCode(Base):
    """Promo codes for bonus generations."""
    __tablename__ = "promo_codes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, index=True, nullable=False)
    bonus_limit = Column(Integer, nullable=False, default=10)  # Extra generations
    max_uses = Column(Integer, nullable=False, default=2)  # Max users who can use
    current_uses = Column(Integer, default=0)  # How many times used
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
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
