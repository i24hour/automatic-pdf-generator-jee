"""
Authentication utilities: password hashing, JWT tokens, and refresh tokens.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db
from models import User, RefreshToken

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token (15 minutes by default)."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(user_id: str, db: Session) -> tuple[str, datetime]:
    """
    Create a long-lived refresh token (7 days by default).
    Stores in database and returns the token string and expiry.
    """
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    refresh_token = RefreshToken(
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token.token, expires_at


def verify_refresh_token(token: str, db: Session) -> Optional[User]:
    """
    Verify a refresh token and return the associated user.
    Returns None if invalid or expired.
    """
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    
    if not refresh_token:
        return None
    
    if refresh_token.expires_at < datetime.utcnow():
        # Token expired, delete it
        db.delete(refresh_token)
        db.commit()
        return None
    
    return db.query(User).filter(User.id == refresh_token.user_id).first()


def revoke_refresh_token(token: str, db: Session) -> bool:
    """Revoke (delete) a refresh token."""
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if refresh_token:
        db.delete(refresh_token)
        db.commit()
        return True
    return False


def revoke_all_user_tokens(user_id: str, db: Session) -> int:
    """Revoke all refresh tokens for a user (logout from all devices)."""
    deleted = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.commit()
    return deleted


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    Returns None if not authenticated (for optional auth).
    """
    if not token:
        return None
    
    payload = decode_token(token)
    if payload is None:
        return None
    
    # Check token type
    if payload.get("type") != "access":
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_current_user_required(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user. Raises 401 if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    # Check token type
    if payload.get("type") != "access":
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_verified_user_required(
    current_user: User = Depends(get_current_user_required)
) -> User:
    """
    Get the current authenticated AND verified user.
    Raises 403 if email not verified.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first."
        )
    return current_user
