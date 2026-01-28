"""
Posts Router - Community feed
Minimal implementation for Cloud Run backend.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from database import get_db
from models import User, SharedPDF, PDFLike, UserBadge
from auth import get_current_user_required, get_current_user

router = APIRouter(prefix="/api/posts", tags=["Posts"])


class CreatePostRequest(BaseModel):
    pdf_id: str
    caption: Optional[str] = None
    visibility: str = "public"


class PostResponse(BaseModel):
    id: str
    user_id: str
    username: Optional[str] = None
    pdf_url: str
    pdf_filename: str
    caption: Optional[str] = None
    subject: str
    topic: str
    level: str
    difficulty: str
    question_count: int
    has_solutions: bool
    visibility: str
    download_count: int
    like_count: int
    view_count: int
    created_at: datetime
    is_liked: bool = False

    class Config:
        from_attributes = True


class FeedResponse(BaseModel):
    posts: List[PostResponse]
    has_more: bool
    next_cursor: Optional[str] = None


class LeaderboardEntry(BaseModel):
    user_id: str
    username: Optional[str] = None
    value: int
    rank: int


class LeaderboardResponse(BaseModel):
    category: str
    entries: List[LeaderboardEntry]


class SetUsernameRequest(BaseModel):
    username: str


@router.post("/set-username")
async def set_username(
    request: SetUsernameRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    username = request.username.strip().lower()
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(status_code=400, detail="Username must be 3-20 characters")

    if not username.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, and underscores")

    existing = db.query(User).filter(User.username == username, User.id != current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    current_user.username = username
    db.commit()
    return {"message": "Username updated", "username": username}


@router.get("", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = None,
    subject: Optional[str] = None,
    level: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SharedPDF).filter(SharedPDF.visibility == "public")

    if subject:
        query = query.filter(SharedPDF.subject == subject)
    if level:
        query = query.filter(SharedPDF.level == level)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.filter(SharedPDF.created_at < cursor_dt)
        except ValueError:
            pass

    posts = query.order_by(desc(SharedPDF.created_at)).limit(limit + 1).all()

    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]

    liked_ids = set()
    if current_user and posts:
        post_ids = [post.id for post in posts]
        liked = db.query(PDFLike).filter(
            PDFLike.user_id == current_user.id,
            PDFLike.shared_pdf_id.in_(post_ids),
        ).all()
        liked_ids = {like.shared_pdf_id for like in liked}

    response_posts = [
        PostResponse(
            id=post.id,
            user_id=post.user_id,
            username=post.user.username if post.user else None,
            pdf_url=post.pdf_url,
            pdf_filename=post.pdf_filename,
            caption=post.caption,
            subject=post.subject,
            topic=post.topic,
            level=post.level,
            difficulty=post.difficulty,
            question_count=post.question_count,
            has_solutions=post.has_solutions,
            visibility=post.visibility,
            download_count=post.download_count,
            like_count=post.like_count,
            view_count=post.view_count,
            created_at=post.created_at,
            is_liked=post.id in liked_ids,
        )
        for post in posts
    ]

    next_cursor = posts[-1].created_at.isoformat() if posts else None

    return FeedResponse(posts=response_posts, has_more=has_more, next_cursor=next_cursor)


@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = db.query(PDFLike).filter(
        PDFLike.user_id == current_user.id,
        PDFLike.shared_pdf_id == post_id,
    ).first()
    if existing:
        return {"like_count": post.like_count}

    like = PDFLike(user_id=current_user.id, shared_pdf_id=post_id)
    post.like_count += 1
    db.add(like)
    db.commit()

    return {"like_count": post.like_count}


@router.delete("/{post_id}/like")
async def unlike_post(
    post_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    like = db.query(PDFLike).filter(
        PDFLike.user_id == current_user.id,
        PDFLike.shared_pdf_id == post_id,
    ).first()

    if like:
        post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
        if post and post.like_count > 0:
            post.like_count -= 1
        db.delete(like)
        db.commit()
        return {"like_count": post.like_count if post else 0}

    return {"like_count": 0}


@router.post("/{post_id}/download")
async def track_download(post_id: str, db: Session = Depends(get_db)):
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.download_count += 1
    db.commit()
    return {"download_count": post.download_count}


@router.get("/leaderboard/most_likes", response_model=LeaderboardResponse)
async def leaderboard_most_likes(db: Session = Depends(get_db)):
    return LeaderboardResponse(category="most_likes", entries=[])


@router.get("/leaderboard/most_posts", response_model=LeaderboardResponse)
async def leaderboard_most_posts(db: Session = Depends(get_db)):
    return LeaderboardResponse(category="most_posts", entries=[])
