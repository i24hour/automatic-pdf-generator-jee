"""
Posts Router - PDF Sharing Community Feature
Handles posting, liking, feed, and leaderboard.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case
from pydantic import BaseModel

from database import get_db
from models import User, SharedPDF, PDFLike, UserBadge
from auth import get_current_user_required, get_current_user

router = APIRouter(prefix="/api/posts", tags=["Posts"])


# ============== Request/Response Models ==============

class CreatePostRequest(BaseModel):
    """Request to create a new post from a generated PDF."""
    pdf_id: str  # ID of the SharedPDF (created during generation)
    caption: Optional[str] = None
    visibility: str = "public"  # public, unlisted, private


class UpdateVisibilityRequest(BaseModel):
    """Request to change post visibility."""
    visibility: str  # public, unlisted, private


class PostResponse(BaseModel):
    """Single post response."""
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
    is_liked: bool = False  # Whether current user liked it
    
    class Config:
        from_attributes = True


class FeedResponse(BaseModel):
    """Paginated feed response."""
    posts: List[PostResponse]
    has_more: bool
    next_cursor: Optional[str] = None


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry."""
    user_id: str
    username: Optional[str] = None
    value: int  # likes or posts count
    rank: int


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""
    category: str  # most_likes, most_posts
    entries: List[LeaderboardEntry]


class BadgeResponse(BaseModel):
    """User badge response."""
    badge_type: str
    earned_at: datetime
    
    class Config:
        from_attributes = True


class SetUsernameRequest(BaseModel):
    """Request to set username."""
    username: str


# ============== Helper Functions ==============

def calculate_feed_score(post: SharedPDF) -> float:
    """
    X.com-like ranking algorithm.
    Score = likes + recency_bonus + engagement_rate
    """
    now = datetime.now(timezone.utc)
    created_at = post.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    hours_old = (now - created_at).total_seconds() / 3600
    
    # Base score from likes
    like_score = post.like_count * 10
    
    # Recency bonus (decays over 48 hours)
    if hours_old < 24:
        recency_bonus = 100 * (1 - hours_old / 24)
    elif hours_old < 48:
        recency_bonus = 50 * (1 - (hours_old - 24) / 24)
    else:
        recency_bonus = 0
    
    # Engagement rate (likes per view, capped)
    if post.view_count > 0:
        engagement_rate = min(post.like_count / post.view_count, 0.5) * 50
    else:
        engagement_rate = 25  # Default for new posts
    
    return like_score + recency_bonus + engagement_rate


def check_and_award_badges(user: User, db: Session):
    """Check and award badges based on user's achievements."""
    badges_to_check = [
        ("first_post", lambda u: u.total_posts >= 1),
        ("prolific", lambda u: u.total_posts >= 10),
        ("century", lambda u: u.total_posts >= 100),
    ]
    
    for badge_type, condition in badges_to_check:
        if condition(user):
            # Check if already has badge
            existing = db.query(UserBadge).filter(
                UserBadge.user_id == user.id,
                UserBadge.badge_type == badge_type
            ).first()
            
            if not existing:
                new_badge = UserBadge(user_id=user.id, badge_type=badge_type)
                db.add(new_badge)
    
    db.commit()


def check_post_badges(post: SharedPDF, db: Session):
    """Check and award badges based on post performance."""
    user = db.query(User).filter(User.id == post.user_id).first()
    if not user:
        return
    
    # Popular badge: 10 likes on a single post
    if post.like_count >= 10:
        existing = db.query(UserBadge).filter(
            UserBadge.user_id == user.id,
            UserBadge.badge_type == "popular"
        ).first()
        if not existing:
            db.add(UserBadge(user_id=user.id, badge_type="popular"))
    
    # Viral badge: 100 likes on a single post
    if post.like_count >= 100:
        existing = db.query(UserBadge).filter(
            UserBadge.user_id == user.id,
            UserBadge.badge_type == "viral"
        ).first()
        if not existing:
            db.add(UserBadge(user_id=user.id, badge_type="viral"))
    
    db.commit()


def enforce_visibility_limits(user: User, db: Session):
    """Enforce private (5) and unlisted (10) limits by deleting oldest."""
    # Private limit: keep last 5
    private_posts = db.query(SharedPDF).filter(
        SharedPDF.user_id == user.id,
        SharedPDF.visibility == "private"
    ).order_by(desc(SharedPDF.created_at)).all()
    
    if len(private_posts) > 5:
        for post in private_posts[5:]:
            db.delete(post)
    
    # Unlisted limit: keep last 10
    unlisted_posts = db.query(SharedPDF).filter(
        SharedPDF.user_id == user.id,
        SharedPDF.visibility == "unlisted"
    ).order_by(desc(SharedPDF.created_at)).all()
    
    if len(unlisted_posts) > 10:
        for post in unlisted_posts[10:]:
            db.delete(post)
    
    db.commit()


# ============== Endpoints ==============

@router.post("/set-username")
async def set_username(
    request: SetUsernameRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Set or update username for the current user."""
    username = request.username.strip().lower()
    
    # Validate username
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(status_code=400, detail="Username must be 3-20 characters")
    
    if not username.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, and underscores")
    
    # Check if taken
    existing = db.query(User).filter(User.username == username, User.id != current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    current_user.username = username
    db.commit()
    
    return {"message": "Username updated", "username": username}


@router.post("", response_model=PostResponse)
async def create_post(
    request: CreatePostRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Post a generated PDF to the community.
    The PDF must already exist in SharedPDF (created during generation).
    """
    # Find the PDF
    pdf = db.query(SharedPDF).filter(
        SharedPDF.id == request.pdf_id,
        SharedPDF.user_id == current_user.id
    ).first()
    
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Check if already public (cannot change)
    if pdf.visibility == "public" and request.visibility != "public":
        raise HTTPException(status_code=400, detail="Public posts cannot be changed to private or unlisted")
    
    # Update post
    pdf.caption = request.caption
    pdf.visibility = request.visibility
    
    # Enforce limits
    enforce_visibility_limits(current_user, db)
    
    # Update user stats if making public
    if request.visibility == "public" and pdf.visibility != "public":
        current_user.total_posts += 1
        check_and_award_badges(current_user, db)
    
    db.commit()
    db.refresh(pdf)
    
    return PostResponse(
        id=pdf.id,
        user_id=pdf.user_id,
        username=current_user.username,
        pdf_url=pdf.pdf_url,
        pdf_filename=pdf.pdf_filename,
        caption=pdf.caption,
        subject=pdf.subject,
        topic=pdf.topic,
        level=pdf.level,
        difficulty=pdf.difficulty,
        question_count=pdf.question_count,
        has_solutions=pdf.has_solutions,
        visibility=pdf.visibility,
        download_count=pdf.download_count,
        like_count=pdf.like_count,
        view_count=pdf.view_count,
        created_at=pdf.created_at,
        is_liked=False
    )


@router.get("", response_model=FeedResponse)
async def get_feed(
    subject: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    cursor: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the public feed with X.com-like ranking algorithm.
    Supports filtering by subject and level.
    """
    # Base query: only public posts
    query = db.query(SharedPDF).filter(SharedPDF.visibility == "public")
    
    # Apply filters
    if subject:
        query = query.filter(SharedPDF.subject == subject)
    if level:
        query = query.filter(SharedPDF.level == level)
    
    # Get all matching posts (for scoring)
    all_posts = query.all()
    
    # Score and sort posts
    scored_posts = [(post, calculate_feed_score(post)) for post in all_posts]
    scored_posts.sort(key=lambda x: x[1], reverse=True)
    
    # Apply cursor pagination (cursor is index-based for simplicity)
    start_idx = int(cursor) if cursor else 0
    end_idx = start_idx + limit
    paginated = scored_posts[start_idx:end_idx]
    
    # Get user's liked posts for is_liked flag
    liked_ids = set()
    if current_user:
        user_likes = db.query(PDFLike.shared_pdf_id).filter(
            PDFLike.user_id == current_user.id
        ).all()
        liked_ids = {like[0] for like in user_likes}
    
    # Build response
    posts = []
    for post, score in paginated:
        user = db.query(User).filter(User.id == post.user_id).first()
        posts.append(PostResponse(
            id=post.id,
            user_id=post.user_id,
            username=user.username if user else None,
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
            is_liked=post.id in liked_ids
        ))
    
    has_more = end_idx < len(scored_posts)
    next_cursor = str(end_idx) if has_more else None
    
    return FeedResponse(posts=posts, has_more=has_more, next_cursor=next_cursor)


@router.get("/my", response_model=List[PostResponse])
async def get_my_posts(
    visibility: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get current user's posts (all visibility levels)."""
    query = db.query(SharedPDF).filter(SharedPDF.user_id == current_user.id)
    
    if visibility:
        query = query.filter(SharedPDF.visibility == visibility)
    
    posts = query.order_by(desc(SharedPDF.created_at)).all()
    
    return [
        PostResponse(
            id=post.id,
            user_id=post.user_id,
            username=current_user.username,
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
            is_liked=False
        )
        for post in posts
    ]


@router.get("/check-existing")
async def check_existing_posts(
    subject: str,
    level: str,
    topic: str,
    db: Session = Depends(get_db)
):
    """
    Check for existing public PDFs matching criteria.
    Used to suggest existing tests before generation.
    Returns the count of matching posts.
    """
    if not topic or len(topic) < 3:
        return {"count": 0}

    # Case insensitive search
    search_term = f"%{topic}%"
    
    count = db.query(SharedPDF).filter(
        SharedPDF.visibility == "public",
        SharedPDF.subject == subject,
        SharedPDF.level == level,
        SharedPDF.topic.ilike(search_term)
    ).count()
    
    return {"count": count}


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single post by ID."""
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check visibility
    if post.visibility == "private":
        if not current_user or current_user.id != post.user_id:
            raise HTTPException(status_code=404, detail="Post not found")
    
    # Increment view count for public/unlisted
    if post.visibility in ["public", "unlisted"]:
        post.view_count += 1
        db.commit()
    
    # Check if liked
    is_liked = False
    if current_user:
        like = db.query(PDFLike).filter(
            PDFLike.user_id == current_user.id,
            PDFLike.shared_pdf_id == post.id
        ).first()
        is_liked = like is not None
    
    user = db.query(User).filter(User.id == post.user_id).first()
    
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        username=user.username if user else None,
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
        is_liked=is_liked
    )


@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Like a post."""
    post = db.query(SharedPDF).filter(
        SharedPDF.id == post_id,
        SharedPDF.visibility == "public"
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if already liked
    existing = db.query(PDFLike).filter(
        PDFLike.user_id == current_user.id,
        PDFLike.shared_pdf_id == post_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already liked")
    
    # Create like
    like = PDFLike(user_id=current_user.id, shared_pdf_id=post_id)
    db.add(like)
    
    # Update counts
    post.like_count += 1
    post_owner = db.query(User).filter(User.id == post.user_id).first()
    if post_owner:
        post_owner.total_likes_received += 1
    
    db.commit()
    
    # Check for badges
    check_post_badges(post, db)
    
    return {"message": "Liked", "like_count": post.like_count}


@router.delete("/{post_id}/like")
async def unlike_post(
    post_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Unlike a post."""
    like = db.query(PDFLike).filter(
        PDFLike.user_id == current_user.id,
        PDFLike.shared_pdf_id == post_id
    ).first()
    
    if not like:
        raise HTTPException(status_code=400, detail="Not liked")
    
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    
    # Remove like
    db.delete(like)
    
    # Update counts
    if post:
        post.like_count = max(0, post.like_count - 1)
        post_owner = db.query(User).filter(User.id == post.user_id).first()
        if post_owner:
            post_owner.total_likes_received = max(0, post_owner.total_likes_received - 1)
    
    db.commit()
    
    return {"message": "Unliked", "like_count": post.like_count if post else 0}


@router.post("/{post_id}/download")
async def track_download(
    post_id: str,
    db: Session = Depends(get_db)
):
    """Track a download (called when user downloads PDF)."""
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    
    if post and post.visibility in ["public", "unlisted"]:
        post.download_count += 1
        db.commit()
    
    return {"message": "Download tracked"}


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Delete a post (Public, Private, or Unlisted)."""
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check ownership
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    # Decrement stats if public
    if post.visibility == "public":
        user = db.query(User).filter(User.id == current_user.id).first()
        if user:
            user.total_posts = max(0, user.total_posts - 1)
            # Remove badges? Maybe too complex. Keep badges.
    
    # Delete likes explicitly? (Cascading usually handles, but let's be safe)
    db.query(PDFLike).filter(PDFLike.shared_pdf_id == post_id).delete()
    
    # Delete post
    db.delete(post)
    db.commit()
    
    return {"message": "Post deleted", "id": post_id}


@router.patch("/{post_id}/visibility")
async def update_post_visibility(
    post_id: str,
    request: UpdateVisibilityRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Change post visibility (private/unlisted to public only)."""
    post = db.query(SharedPDF).filter(SharedPDF.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check ownership
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    # Prevent downgrading public posts
    if post.visibility == "public" and request.visibility != "public":
        raise HTTPException(status_code=400, detail="Public posts cannot be changed to private or unlisted")
    
    old_visibility = post.visibility
    post.visibility = request.visibility
    
    # If making public, increment total_posts and award badges
    if request.visibility == "public" and old_visibility != "public":
        current_user.total_posts += 1
        check_and_award_badges(current_user, db)
    
    db.commit()
    db.refresh(post)
    
    return {
        "message": f"Post visibility changed to {request.visibility}",
        "id": post_id,
        "visibility": post.visibility
    }


@router.get("/leaderboard/{category}", response_model=LeaderboardResponse)
async def get_leaderboard(
    category: str,  # most_likes, most_posts
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db)
):
    """Get leaderboard by category."""
    if category == "most_likes":
        results = db.query(User).filter(
            User.total_likes_received > 0
        ).order_by(desc(User.total_likes_received)).limit(limit).all()
        
        entries = [
            LeaderboardEntry(
                user_id=user.id,
                username=user.username,
                value=user.total_likes_received,
                rank=idx + 1
            )
            for idx, user in enumerate(results)
        ]
    
    elif category == "most_posts":
        results = db.query(User).filter(
            User.total_posts > 0
        ).order_by(desc(User.total_posts)).limit(limit).all()
        
        entries = [
            LeaderboardEntry(
                user_id=user.id,
                username=user.username,
                value=user.total_posts,
                rank=idx + 1
            )
            for idx, user in enumerate(results)
        ]
    
    else:
        raise HTTPException(status_code=400, detail="Invalid category. Use: most_likes, most_posts")
    
    return LeaderboardResponse(category=category, entries=entries)


@router.get("/badges/my", response_model=List[BadgeResponse])
async def get_my_badges(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get current user's badges."""
    badges = db.query(UserBadge).filter(UserBadge.user_id == current_user.id).all()
    return [BadgeResponse(badge_type=b.badge_type, earned_at=b.earned_at) for b in badges]

