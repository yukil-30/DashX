"""
Chat Router
Handles chat queries, KB search, LLM fallback, and rating system.

Flow:
-----
1. POST /chat/query - User asks a question
   - Search knowledge_base for matching answers (full-text search)
   - If high-confidence match found: return KB answer
   - If no match or low confidence: call LLM adapter
   - Store chat log and return chat_id for rating

2. POST /chat/{chat_id}/rate - User rates the answer
   - Rating 0 = flagged for manager review
   - Rating 1-5 = satisfaction score

3. GET /chat/flagged - Manager views flagged answers
4. POST /chat/{chat_id}/review - Manager reviews flagged entry

5. CRUD for knowledge_base (manager only)
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_

from app.database import get_db
from app.models import Account, KnowledgeBase, ChatLog, KBContribution
from app.schemas import (
    ChatQueryRequest, ChatQueryResponse,
    ChatRateRequest, ChatRateResponse,
    KnowledgeBaseEntry, KnowledgeBaseCreateRequest, KnowledgeBaseUpdateRequest,
    FlaggedChatResponse, FlaggedChatListResponse,
    ReviewFlaggedRequest, ReviewFlaggedResponse,
    KBContributionCreateRequest, KBContributionResponse, KBContributionListResponse,
    KBContributionReviewRequest, KBContributionReviewResponse
)
from app.auth import get_current_user, get_current_user_optional, require_manager
from app.llm_adapter import get_llm_adapter, LLMResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Confidence threshold for KB answers
KB_CONFIDENCE_THRESHOLD = float(os.getenv("KB_CONFIDENCE_THRESHOLD", "0.6"))


def get_iso_now() -> str:
    """Get current timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def search_knowledge_base(
    db: Session, 
    question: str, 
    min_confidence: float = KB_CONFIDENCE_THRESHOLD
) -> Optional[tuple[KnowledgeBase, float]]:
    """
    Search knowledge base using PostgreSQL full-text search.
    Returns (kb_entry, match_score) or None if no good match.
    """
    # Normalize the question for search
    search_query = " | ".join(question.lower().split())
    
    try:
        # Use full-text search with ts_rank for relevance scoring
        result = db.execute(
            text("""
                SELECT 
                    id, 
                    question, 
                    answer, 
                    keywords, 
                    confidence,
                    author_id,
                    is_active,
                    created_at,
                    ts_rank(search_vector, plainto_tsquery('english', :query)) as rank
                FROM knowledge_base
                WHERE is_active = TRUE
                  AND search_vector @@ plainto_tsquery('english', :query)
                ORDER BY rank DESC, confidence DESC
                LIMIT 1
            """),
            {"query": question}
        ).fetchone()
        
        if result:
            # Create KnowledgeBase object from result
            kb_entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == result[0]).first()
            match_score = float(result[8]) if result[8] else 0.0
            
            # Combine match score with KB confidence
            effective_confidence = (match_score * 0.5 + float(kb_entry.confidence) * 0.5)
            
            if effective_confidence >= min_confidence:
                logger.info(f"KB match found: id={kb_entry.id}, score={effective_confidence:.2f}")
                return (kb_entry, effective_confidence)
            else:
                logger.debug(f"KB match below threshold: score={effective_confidence:.2f} < {min_confidence}")
    
    except Exception as e:
        logger.warning(f"Full-text search failed, falling back to LIKE: {e}")
        # Fallback to simple LIKE search
        return _fallback_like_search(db, question, min_confidence)
    
    return None


def _fallback_like_search(
    db: Session, 
    question: str, 
    min_confidence: float
) -> Optional[tuple[KnowledgeBase, float]]:
    """Fallback LIKE search when full-text search is unavailable"""
    words = question.lower().split()[:5]  # Use first 5 words
    
    # Build OR conditions for each word
    conditions = []
    for word in words:
        if len(word) >= 3:  # Skip short words
            pattern = f"%{word}%"
            conditions.append(
                or_(
                    func.lower(KnowledgeBase.question).like(pattern),
                    func.lower(KnowledgeBase.keywords).like(pattern)
                )
            )
    
    if not conditions:
        return None
    
    kb_entry = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.is_active == True)
        .filter(or_(*conditions))
        .order_by(KnowledgeBase.confidence.desc())
        .first()
    )
    
    if kb_entry and float(kb_entry.confidence) >= min_confidence:
        return (kb_entry, float(kb_entry.confidence))
    
    return None


# ============================================================
# Chat Query Endpoint
# ============================================================

@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Account] = Depends(get_current_user_optional)
):
    """
    Submit a question to the chat system.
    
    Flow:
    1. Search knowledge base for matching answer
    2. If found with high confidence, return KB answer
    3. If not found, call LLM adapter for response
    4. Store chat log and return chat_id for rating
    """
    # Determine user_id
    user_id = request.user_id
    if current_user:
        user_id = current_user.ID
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id required (provide in request or authenticate)"
        )
    
    # Verify user exists
    user = db.query(Account).filter(Account.ID == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    question = request.question.strip()
    
    # Step 1: Search knowledge base
    kb_result = search_knowledge_base(db, question)
    
    if kb_result:
        kb_entry, confidence = kb_result
        
        # Create chat log with KB answer
        chat_log = ChatLog(
            user_id=user_id,
            question=question,
            answer=kb_entry.answer,
            source="kb",
            kb_entry_id=kb_entry.id,
            confidence=Decimal(str(round(confidence, 2))),
            created_at=get_iso_now()
        )
        db.add(chat_log)
        db.commit()
        db.refresh(chat_log)
        
        logger.info(f"Chat {chat_log.id}: KB answer returned (confidence={confidence:.2f})")
        
        return ChatQueryResponse(
            chat_id=chat_log.id,
            question=question,
            answer=kb_entry.answer,
            source="kb",
            confidence=confidence,
            kb_entry_id=kb_entry.id
        )
    
    # Step 2: No KB match - call LLM adapter
    adapter = get_llm_adapter()
    logger.info(f"No KB match, calling LLM adapter: {adapter.name}")
    
    # Provide context to LLM
    context = (
        "You are a helpful assistant for DashX restaurant. "
        "Answer the user's question about the menu or order politely and concisely."
    )
    
    llm_response: LLMResponse = await adapter.generate(question, context)
    
    if llm_response.error:
        logger.error(f"LLM error: {llm_response.error}")
        # Return a fallback response
        answer = "I'm sorry, I couldn't process your question at the moment. Please try again later or contact our staff."
        confidence = 0.0
    else:
        answer = llm_response.answer
        confidence = llm_response.confidence
    
    # Create chat log with LLM answer
    chat_log = ChatLog(
        user_id=user_id,
        question=question,
        answer=answer,
        source="llm",
        kb_entry_id=None,
        confidence=Decimal(str(round(confidence, 2))),
        created_at=get_iso_now()
    )
    db.add(chat_log)
    db.commit()
    db.refresh(chat_log)
    
    logger.info(f"Chat {chat_log.id}: LLM answer returned (model={llm_response.model}, cached={llm_response.cached})")
    
    return ChatQueryResponse(
        chat_id=chat_log.id,
        question=question,
        answer=answer,
        source="llm",
        confidence=confidence,
        kb_entry_id=None
    )


# ============================================================
# Rating Endpoint
# ============================================================

@router.post("/{chat_id}/rate", response_model=ChatRateResponse)
async def rate_chat(
    chat_id: int,
    request: ChatRateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Account] = Depends(get_current_user_optional)
):
    """
    Rate a chat response.
    
    Rating scale:
    - 0: Flag for manager review (answer was wrong/harmful)
    - 1-5: Satisfaction score
    """
    chat_log = db.query(ChatLog).filter(ChatLog.id == chat_id).first()
    
    if not chat_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {chat_id} not found"
        )
    
    # Optional: verify user owns this chat
    if current_user and chat_log.user_id != current_user.ID:
        # Allow rating but log it
        logger.warning(f"User {current_user.ID} rating chat {chat_id} owned by user {chat_log.user_id}")
    
    chat_log.rating = request.rating
    
    # Flag if rating is 0
    if request.rating == 0:
        chat_log.flagged = True
        logger.warning(f"Chat {chat_id} flagged for manager review (rating=0)")
    
    db.commit()
    
    return ChatRateResponse(
        message="Rating recorded" if request.rating > 0 else "Flagged for manager review",
        chat_id=chat_id,
        rating=request.rating,
        flagged=chat_log.flagged
    )


# ============================================================
# Manager Endpoints - Flagged Answers
# ============================================================

@router.get("/flagged", response_model=FlaggedChatListResponse)
async def get_flagged_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_reviewed: bool = Query(False, description="Include already-reviewed entries"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Get list of flagged chat entries for manager review.
    Manager only.
    """
    query = db.query(ChatLog).filter(ChatLog.flagged == True)
    
    if not include_reviewed:
        query = query.filter(ChatLog.reviewed == False)
    
    total = query.count()
    
    flagged_chats = query.order_by(ChatLog.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enrich with user email
    results = []
    for chat in flagged_chats:
        user = db.query(Account).filter(Account.ID == chat.user_id).first()
        results.append(FlaggedChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            user_email=user.email if user else None,
            question=chat.question,
            answer=chat.answer,
            source=chat.source,
            confidence=float(chat.confidence) if chat.confidence else None,
            rating=chat.rating,
            kb_entry_id=chat.kb_entry_id,
            created_at=chat.created_at,
            reviewed=chat.reviewed
        ))
    
    return FlaggedChatListResponse(
        flagged_chats=results,
        total=total
    )


@router.post("/{chat_id}/review", response_model=ReviewFlaggedResponse)
async def review_flagged_chat(
    chat_id: int,
    request: ReviewFlaggedRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Review a flagged chat entry.
    Manager only.
    
    Actions:
    - dismiss: Mark as reviewed, no further action
    - remove_kb: Remove the KB entry that provided the answer
    - disable_author: Deactivate all KB entries from the author
    """
    chat_log = db.query(ChatLog).filter(ChatLog.id == chat_id).first()
    
    if not chat_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {chat_id} not found"
        )
    
    if not chat_log.flagged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is not flagged"
        )
    
    kb_entries_affected = 0
    action_taken = request.action
    
    if request.action == "remove_kb":
        if chat_log.kb_entry_id:
            kb_entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == chat_log.kb_entry_id).first()
            if kb_entry:
                kb_entry.is_active = False
                kb_entries_affected = 1
                logger.info(f"KB entry {kb_entry.id} deactivated by manager {current_user.ID}")
        else:
            action_taken = "dismiss"  # No KB entry to remove
    
    elif request.action == "disable_author":
        if chat_log.kb_entry_id:
            kb_entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == chat_log.kb_entry_id).first()
            if kb_entry and kb_entry.author_id:
                # Deactivate all entries by this author
                kb_entries_affected = (
                    db.query(KnowledgeBase)
                    .filter(KnowledgeBase.author_id == kb_entry.author_id)
                    .filter(KnowledgeBase.is_active == True)
                    .update({"is_active": False})
                )
                logger.warning(
                    f"All KB entries by author {kb_entry.author_id} deactivated "
                    f"({kb_entries_affected} entries) by manager {current_user.ID}"
                )
        else:
            action_taken = "dismiss"  # No author to disable
    
    # Mark as reviewed
    chat_log.reviewed = True
    chat_log.reviewed_by = current_user.ID
    chat_log.reviewed_at = get_iso_now()
    
    db.commit()
    
    return ReviewFlaggedResponse(
        message=f"Chat {chat_id} reviewed",
        chat_id=chat_id,
        action_taken=action_taken,
        kb_entries_affected=kb_entries_affected
    )


# ============================================================
# Knowledge Base CRUD (Manager Only)
# ============================================================

@router.get("/kb", response_model=List[KnowledgeBaseEntry])
async def list_knowledge_base(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """List knowledge base entries. Manager only."""
    query = db.query(KnowledgeBase)
    
    if active_only:
        query = query.filter(KnowledgeBase.is_active == True)
    
    entries = query.order_by(KnowledgeBase.id.desc()).offset(skip).limit(limit).all()
    
    return [
        KnowledgeBaseEntry(
            id=e.id,
            question=e.question,
            answer=e.answer,
            keywords=e.keywords,
            confidence=float(e.confidence),
            author_id=e.author_id,
            is_active=e.is_active,
            created_at=e.created_at
        )
        for e in entries
    ]


@router.post("/kb", response_model=KnowledgeBaseEntry, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base_entry(
    request: KnowledgeBaseCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """Create a new knowledge base entry. Manager only."""
    kb_entry = KnowledgeBase(
        question=request.question,
        answer=request.answer,
        keywords=request.keywords,
        confidence=Decimal(str(request.confidence)),
        author_id=current_user.ID,
        is_active=True,
        created_at=get_iso_now(),
        updated_at=get_iso_now()
    )
    
    db.add(kb_entry)
    db.commit()
    db.refresh(kb_entry)
    
    logger.info(f"KB entry {kb_entry.id} created by manager {current_user.ID}")
    
    return KnowledgeBaseEntry(
        id=kb_entry.id,
        question=kb_entry.question,
        answer=kb_entry.answer,
        keywords=kb_entry.keywords,
        confidence=float(kb_entry.confidence),
        author_id=kb_entry.author_id,
        is_active=kb_entry.is_active,
        created_at=kb_entry.created_at
    )


@router.put("/kb/{kb_id}", response_model=KnowledgeBaseEntry)
async def update_knowledge_base_entry(
    kb_id: int,
    request: KnowledgeBaseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """Update a knowledge base entry. Manager only."""
    kb_entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    
    if not kb_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KB entry {kb_id} not found"
        )
    
    # Update fields if provided
    if request.question is not None:
        kb_entry.question = request.question
    if request.answer is not None:
        kb_entry.answer = request.answer
    if request.keywords is not None:
        kb_entry.keywords = request.keywords
    if request.confidence is not None:
        kb_entry.confidence = Decimal(str(request.confidence))
    if request.is_active is not None:
        kb_entry.is_active = request.is_active
    
    kb_entry.updated_at = get_iso_now()
    
    db.commit()
    db.refresh(kb_entry)
    
    logger.info(f"KB entry {kb_id} updated by manager {current_user.ID}")
    
    return KnowledgeBaseEntry(
        id=kb_entry.id,
        question=kb_entry.question,
        answer=kb_entry.answer,
        keywords=kb_entry.keywords,
        confidence=float(kb_entry.confidence),
        author_id=kb_entry.author_id,
        is_active=kb_entry.is_active,
        created_at=kb_entry.created_at
    )


@router.delete("/kb/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base_entry(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """Soft-delete a knowledge base entry (set is_active=False). Manager only."""
    kb_entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    
    if not kb_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KB entry {kb_id} not found"
        )
    
    kb_entry.is_active = False
    kb_entry.updated_at = get_iso_now()
    
    db.commit()
    
    logger.info(f"KB entry {kb_id} soft-deleted by manager {current_user.ID}")


# ============================================================
# Chat History Endpoint
# ============================================================

@router.get("/history")
async def get_chat_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Get user's chat history.
    Returns list of past chat interactions with ratings.
    """
    chats = (
        db.query(ChatLog)
        .filter(ChatLog.user_id == current_user.ID)
        .order_by(ChatLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": chat.id,
            "question": chat.question,
            "answer": chat.answer,
            "source": chat.source,
            "confidence": float(chat.confidence) if chat.confidence else None,
            "rating": chat.rating,
            "created_at": chat.created_at
        }
        for chat in chats
    ]


# ============================================================
# LLM Adapter Health/Stats
# ============================================================

@router.get("/adapter/health")
async def get_adapter_health(
    current_user: Account = Depends(require_manager)
):
    """Get LLM adapter health status. Manager only."""
    adapter = get_llm_adapter()
    health = adapter.health_check()
    
    from app.llm_adapter import get_llm_cache
    cache = get_llm_cache()
    
    return {
        "adapter": health,
        "cache": cache.stats()
    }


@router.post("/adapter/cache/clear")
async def clear_adapter_cache(
    current_user: Account = Depends(require_manager)
):
    """Clear LLM response cache. Manager only."""
    from app.llm_adapter import get_llm_cache
    cache = get_llm_cache()
    cache.clear()
    
    logger.info(f"LLM cache cleared by manager {current_user.ID}")
    
    return {"message": "Cache cleared"}


# ============================================================
# Stats Endpoint
# ============================================================

@router.get("/stats")
async def get_chat_stats(
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Get chat system statistics. Manager only.
    """
    total_chats = db.query(ChatLog).count()
    kb_chats = db.query(ChatLog).filter(ChatLog.source == "kb").count()
    llm_chats = db.query(ChatLog).filter(ChatLog.source == "llm").count()
    flagged_count = db.query(ChatLog).filter(ChatLog.flagged == True).count()
    reviewed_count = db.query(ChatLog).filter(ChatLog.reviewed == True).count()
    
    # Average ratings
    from sqlalchemy import func as sqlfunc
    avg_rating = db.query(sqlfunc.avg(ChatLog.rating)).filter(ChatLog.rating > 0).scalar()
    
    # KB stats
    total_kb = db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True).count()
    
    return {
        "total_chats": total_chats,
        "kb_chats": kb_chats,
        "llm_chats": llm_chats,
        "kb_hit_rate": kb_chats / total_chats if total_chats > 0 else 0,
        "flagged_count": flagged_count,
        "pending_review": flagged_count - reviewed_count,
        "average_rating": float(avg_rating) if avg_rating else None,
        "total_kb_entries": total_kb
    }


# ============================================================
# KB Contribution Endpoints (Customer submissions)
# ============================================================

@router.post("/kb/contribute", response_model=KBContributionResponse, status_code=status.HTTP_201_CREATED)
async def submit_kb_contribution(
    request: KBContributionCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Submit a knowledge base contribution for manager review.
    Available to all authenticated users (customers, VIPs, etc.).
    """
    # Create contribution record
    contribution = KBContribution(
        submitter_id=current_user.ID,
        question=request.question.strip(),
        answer=request.answer.strip(),
        keywords=request.keywords.strip() if request.keywords else None,
        status="pending",
        created_at=get_iso_now(),
        updated_at=get_iso_now()
    )
    
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    
    logger.info(f"KB contribution {contribution.id} submitted by user {current_user.ID}")
    
    return KBContributionResponse(
        id=contribution.id,
        submitter_id=contribution.submitter_id,
        submitter_email=current_user.email,
        question=contribution.question,
        answer=contribution.answer,
        keywords=contribution.keywords,
        status=contribution.status,
        rejection_reason=None,
        reviewed_by=None,
        reviewer_email=None,
        reviewed_at=None,
        created_kb_entry_id=None,
        created_at=contribution.created_at
    )


@router.get("/kb/contributions", response_model=KBContributionListResponse)
async def list_kb_contributions(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    List KB contributions for manager review.
    Manager only.
    """
    query = db.query(KBContribution)
    
    if status_filter:
        query = query.filter(KBContribution.status == status_filter)
    
    total = query.count()
    pending_count = db.query(KBContribution).filter(KBContribution.status == "pending").count()
    
    contributions = query.order_by(KBContribution.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for c in contributions:
        submitter = db.query(Account).filter(Account.ID == c.submitter_id).first()
        reviewer = db.query(Account).filter(Account.ID == c.reviewed_by).first() if c.reviewed_by else None
        
        results.append(KBContributionResponse(
            id=c.id,
            submitter_id=c.submitter_id,
            submitter_email=submitter.email if submitter else None,
            question=c.question,
            answer=c.answer,
            keywords=c.keywords,
            status=c.status,
            rejection_reason=c.rejection_reason,
            reviewed_by=c.reviewed_by,
            reviewer_email=reviewer.email if reviewer else None,
            reviewed_at=c.reviewed_at,
            created_kb_entry_id=c.created_kb_entry_id,
            created_at=c.created_at
        ))
    
    return KBContributionListResponse(
        contributions=results,
        total=total,
        pending_count=pending_count
    )


@router.get("/kb/contributions/mine")
async def get_my_kb_contributions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Get current user's KB contributions and their status.
    """
    query = db.query(KBContribution).filter(KBContribution.submitter_id == current_user.ID)
    
    total = query.count()
    contributions = query.order_by(KBContribution.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "contributions": [
            {
                "id": c.id,
                "question": c.question,
                "answer": c.answer[:200] + "..." if len(c.answer) > 200 else c.answer,
                "status": c.status,
                "rejection_reason": c.rejection_reason,
                "created_at": c.created_at
            }
            for c in contributions
        ],
        "total": total
    }


@router.post("/kb/contributions/{contribution_id}/review", response_model=KBContributionReviewResponse)
async def review_kb_contribution(
    contribution_id: int,
    request: KBContributionReviewRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Approve or reject a KB contribution.
    Manager only.
    
    If approved, creates a new KnowledgeBase entry with the contribution content.
    """
    contribution = db.query(KBContribution).filter(KBContribution.id == contribution_id).first()
    
    if not contribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KB contribution {contribution_id} not found"
        )
    
    if contribution.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contribution is already {contribution.status}"
        )
    
    created_kb_entry_id = None
    
    if request.action == "approve":
        # Create new KB entry from contribution
        kb_entry = KnowledgeBase(
            question=contribution.question,
            answer=contribution.answer,
            keywords=contribution.keywords,
            confidence=Decimal(str(request.confidence)),
            author_id=contribution.submitter_id,
            is_active=True,
            created_at=get_iso_now(),
            updated_at=get_iso_now()
        )
        db.add(kb_entry)
        db.flush()  # Get the ID
        
        contribution.status = "approved"
        contribution.created_kb_entry_id = kb_entry.id
        created_kb_entry_id = kb_entry.id
        
        logger.info(
            f"KB contribution {contribution_id} approved by manager {current_user.ID}, "
            f"created KB entry {kb_entry.id}"
        )
    
    elif request.action == "reject":
        if not request.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        
        contribution.status = "rejected"
        contribution.rejection_reason = request.rejection_reason
        
        logger.info(f"KB contribution {contribution_id} rejected by manager {current_user.ID}")
    
    contribution.reviewed_by = current_user.ID
    contribution.reviewed_at = get_iso_now()
    contribution.updated_at = get_iso_now()
    
    db.commit()
    
    return KBContributionReviewResponse(
        message=f"KB contribution {request.action}d successfully",
        contribution_id=contribution_id,
        status=contribution.status,
        created_kb_entry_id=created_kb_entry_id
    )
