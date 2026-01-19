"""
Authentication router: register, login, refresh, verify, and password reset endpoints.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

from database import get_db
from models import User, RefreshToken, VerificationToken, PasswordResetToken
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_user_required,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from services.email_service import email_service

load_dotenv()

VERIFICATION_TOKEN_EXPIRE_HOURS = int(os.getenv("VERIFICATION_TOKEN_EXPIRE_HOURS", "24"))
RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("RESET_TOKEN_EXPIRE_HOURS", "1"))

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    name: str = None
    phone: str = None
    phone: str = None


class UserUpdate(BaseModel):
    """User profile update request."""
    name: Optional[str] = None
    phone: Optional[str] = None
    class_grade: Optional[str] = None
    username: Optional[str] = None
class UserResponse(BaseModel):
    """User response (without password)."""
    id: str
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    class_grade: Optional[str] = None
    is_verified: bool = False
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response with refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    user: UserResponse


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Access token only response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    """Verify email request."""
    token: str


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# Helper Functions
def create_verification_token(user_id: str, db: Session) -> str:
    """Create an email verification token."""
    # Delete any existing tokens for this user
    db.query(VerificationToken).filter(VerificationToken.user_id == user_id).delete()
    
    expires_at = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    token = VerificationToken(user_id=user_id, expires_at=expires_at)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token.token


def create_password_reset_token(user_id: str, db: Session) -> str:
    """Create a password reset token."""
    # Delete any existing tokens for this user
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
    
    expires_at = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    token = PasswordResetToken(user_id=user_id, expires_at=expires_at)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token.token


# Endpoints
@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        name=user_data.name,
        phone=user_data.phone,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create verification token and send email
    verification_token = create_verification_token(new_user.id, db)
    background_tasks.add_task(
        email_service.send_verification_email,
        new_user.email,
        new_user.name,
        verification_token
    )
    
    # Create tokens
    access_token = create_access_token(data={"sub": new_user.id})
    refresh_token, _ = create_refresh_token(new_user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access + refresh tokens."""
    # Find user
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token, _ = create_refresh_token(user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


class GoogleAuthRequest(BaseModel):
    """Google OAuth request with ID token."""
    credential: str  # Google ID token


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate with Google OAuth.
    Verifies Google ID token and creates/logs in user.
    """
    import requests
    
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "87253755436-sovpsbdnimbques0hnhstgjuc78l532p.apps.googleusercontent.com")
    
    try:
        # Verify token with Google
        google_response = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={request.credential}"
        )
        
        if google_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        
        token_info = google_response.json()
        
        # Verify audience (client ID)
        if token_info.get("aud") != GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not intended for this app"
            )
        
        email = token_info.get("email")
        name = token_info.get("name", "")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user (auto-verified since Google verified the email)
            user = User(
                email=email,
                name=name,
                hashed_password=get_password_hash(os.urandom(32).hex()),  # Random password
                is_verified=True  # Google-authenticated users are auto-verified
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create tokens
        access_token = create_access_token(data={"sub": user.id})
        refresh_token, _ = create_refresh_token(user.id, db)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        )
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not verify Google token: {str(e)}"
        )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """Get a new access token using refresh token."""
    user = verify_refresh_token(request.refresh_token, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": user.id})
    
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Logout and revoke refresh token."""
    revoke_refresh_token(request.refresh_token, db)
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Logout from all devices."""
    count = revoke_all_user_tokens(current_user.id, db)
    return MessageResponse(message=f"Logged out from {count} device(s)")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_required)
):
    """Get current authenticated user info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
        username=current_user.username,
        class_grade=current_user.class_grade,
        is_verified=current_user.is_verified
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with token."""
    token = db.query(VerificationToken).filter(VerificationToken.token == request.token).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Make expires_at timezone-aware if it's naive
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        db.delete(token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )
    
    # Mark user as verified
    user = db.query(User).filter(User.id == token.user_id).first()
    if user:
        user.is_verified = True
        db.delete(token)
        db.commit()
    
    return MessageResponse(message="Email verified successfully!")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Resend verification email."""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Create new verification token and send email
    verification_token = create_verification_token(current_user.id, db)
    background_tasks.add_task(
        email_service.send_verification_email,
        current_user.email,
        current_user.name,
        verification_token
    )
    
    return MessageResponse(message="Verification email sent!")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send password reset email."""
    user = db.query(User).filter(User.email == request.email).first()
    
    # Always return success to prevent email enumeration
    if not user:
        return MessageResponse(message="If an account exists with this email, you will receive a password reset link.")
    
    # Create reset token and send email
    reset_token = create_password_reset_token(user.id, db)
    background_tasks.add_task(
        email_service.send_password_reset_email,
        user.email,
        user.name,
        reset_token
    )
    
    return MessageResponse(message="If an account exists with this email, you will receive a password reset link.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token."""
    token = db.query(PasswordResetToken).filter(PasswordResetToken.token == request.token).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Make expires_at timezone-aware if it's naive
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        db.delete(token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    
    # Update password
    user = db.query(User).filter(User.id == token.user_id).first()
    if user:
        user.hashed_password = get_password_hash(request.new_password)
        db.delete(token)
        # Revoke all refresh tokens for security
        revoke_all_user_tokens(user.id, db)
        db.commit()
    
    return MessageResponse(message="Password reset successfully! Please login with your new password.")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user_required)):
    """Get current user info."""
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    # Check if username is taken if being updated
    if user_update.username and user_update.username != current_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username

    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.class_grade is not None:
        current_user.class_grade = user_update.class_grade
    
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
