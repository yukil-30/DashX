"""
Forum Router
Discussion forum for chef/dish/delivery topics.
- Create threads
- List threads
- View thread with posts
- Add posts (comments)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, get_current_user_optional
from app.models import Account, Thread, Post, Restaurant
from app.schemas import (
    ThreadCreateRequest, ThreadResponse, ThreadDetailResponse,
    ThreadListResponse, PostCreateRequest, PostResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forum", tags=["Forum"])


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    restaurant_id: Optional[int] = Query(None, description="Filter by restaurant"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    List all forum threads with pagination.
    Optionally filter by restaurant or category.
    """
    query = db.query(Thread).options(
        joinedload(Thread.posts),
        joinedload(Thread.restaurant)
    )
    
    if restaurant_id:
        query = query.filter(Thread.restaurantID == restaurant_id)
    
    total = query.count()
    offset = (page - 1) * per_page
    
    threads = query.order_by(desc(Thread.id)).offset(offset).limit(per_page).all()
    
    result = []
    for thread in threads:
        # Get first post for created_by info
        first_post = None
        if thread.posts:
            first_post = min(thread.posts, key=lambda p: p.id)
        
        result.append(ThreadDetailResponse(
            id=thread.id,
            topic=thread.topic,
            restaurantID=thread.restaurantID,
            created_by_id=first_post.posterID if first_post else 0,
            created_by_email=first_post.poster.email if first_post and first_post.poster else None,
            posts_count=len(thread.posts),
            created_at=first_post.datetime if first_post else None,
            posts=[]  # Don't include posts in list view
        ))
    
    return ThreadListResponse(
        threads=result,
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/threads", response_model=ThreadDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    request: ThreadCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Create a new forum thread with an initial post.
    """
    # Verify restaurant exists (use default if not specified)
    restaurant_id = getattr(request, 'restaurantID', None) or 1
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        # Use default restaurant
        restaurant = db.query(Restaurant).first()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No restaurant available"
            )
        restaurant_id = restaurant.id
    
    # Create thread
    thread = Thread(
        topic=request.topic,
        restaurantID=restaurant_id
    )
    db.add(thread)
    db.flush()  # Get thread ID
    
    # Create initial post
    now = datetime.now(timezone.utc).isoformat()
    post = Post(
        threadID=thread.id,
        posterID=current_user.ID,
        title=request.topic,
        body=request.body,
        datetime=now
    )
    db.add(post)
    
    db.commit()
    db.refresh(thread)
    
    logger.info(f"Thread created: {thread.id} by user {current_user.ID}")
    
    return ThreadDetailResponse(
        id=thread.id,
        topic=thread.topic,
        restaurantID=thread.restaurantID,
        created_by_id=current_user.ID,
        created_by_email=current_user.email,
        posts_count=1,
        created_at=now,
        posts=[PostResponse(
            id=post.id,
            threadID=post.threadID,
            posterID=post.posterID,
            title=post.title,
            body=post.body,
            datetime=post.datetime
        )]
    )


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a thread with all its posts.
    """
    thread = db.query(Thread).options(
        joinedload(Thread.posts).joinedload(Post.poster)
    ).filter(Thread.id == thread_id).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Sort posts by ID (chronological)
    posts = sorted(thread.posts, key=lambda p: p.id)
    
    first_post = posts[0] if posts else None
    
    return ThreadDetailResponse(
        id=thread.id,
        topic=thread.topic,
        restaurantID=thread.restaurantID,
        created_by_id=first_post.posterID if first_post else 0,
        created_by_email=first_post.poster.email if first_post and first_post.poster else None,
        posts_count=len(posts),
        created_at=first_post.datetime if first_post else None,
        posts=[
            PostResponse(
                id=p.id,
                threadID=p.threadID,
                posterID=p.posterID,
                title=p.title,
                body=p.body,
                datetime=p.datetime
            )
            for p in posts
        ]
    )


@router.post("/threads/{thread_id}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def add_post(
    thread_id: int,
    request: PostCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Add a post (comment) to a thread.
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    post = Post(
        threadID=thread_id,
        posterID=current_user.ID,
        title=request.title,
        body=request.body,
        datetime=now
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    
    logger.info(f"Post created: {post.id} in thread {thread_id} by user {current_user.ID}")
    
    return PostResponse(
        id=post.id,
        threadID=post.threadID,
        posterID=post.posterID,
        title=post.title,
        body=post.body,
        datetime=post.datetime
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Delete a thread (only by creator or manager).
    """
    thread = db.query(Thread).options(
        joinedload(Thread.posts)
    ).filter(Thread.id == thread_id).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Check permission
    first_post = min(thread.posts, key=lambda p: p.id) if thread.posts else None
    is_creator = first_post and first_post.posterID == current_user.ID
    is_manager = current_user.type == 'manager'
    
    if not is_creator and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread creator or manager can delete"
        )
    
    db.delete(thread)
    db.commit()
    
    logger.info(f"Thread deleted: {thread_id} by user {current_user.ID}")


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Delete a post (only by creator or manager).
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permission
    is_creator = post.posterID == current_user.ID
    is_manager = current_user.type == 'manager'
    
    if not is_creator and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only post creator or manager can delete"
        )
    
    db.delete(post)
    db.commit()
    
    logger.info(f"Post deleted: {post_id} by user {current_user.ID}")
