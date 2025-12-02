"""
Tests for Chat System
Covers:
- KB search returning matches
- LLM fallback when no KB match
- Rating system (including flagging)
- Manager review of flagged entries
- KB CRUD operations
- Caching behavior
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

from app.main import app
from app.auth import create_access_token, get_current_user
from app.database import get_db
from app.llm_adapter import (
    LLMResponse, LLMCache, StubAdapter, OllamaAdapter, 
    get_llm_adapter, get_llm_cache
)


# Create test client
client = TestClient(app)


# ============================================================
# Mock Factories
# ============================================================

def create_mock_user(ID=1, email="test@example.com", type="customer"):
    """Create a mock user"""
    mock = MagicMock()
    mock.ID = ID
    mock.email = email
    mock.type = type
    mock.balance = 5000
    mock.warnings = 0
    return mock


def create_mock_manager(ID=99, email="manager@example.com"):
    """Create a mock manager user"""
    return create_mock_user(ID=ID, email=email, type="manager")


def create_mock_kb_entry(
    id=1,
    question="What are your hours?",
    answer="We are open Monday-Sunday, 11am-10pm.",
    keywords="hours,open,schedule",
    confidence=0.85
):
    """Create a mock knowledge base entry"""
    mock = MagicMock()
    mock.id = id
    mock.question = question
    mock.answer = answer
    mock.keywords = keywords
    mock.confidence = Decimal(str(confidence))
    mock.author_id = 1
    mock.is_active = True
    mock.created_at = datetime.now(timezone.utc).isoformat()
    mock.updated_at = mock.created_at
    return mock


def create_mock_chat_log(
    id=1,
    user_id=1,
    question="What are your hours?",
    answer="We are open Monday-Sunday, 11am-10pm.",
    source="kb",
    kb_entry_id=1,
    confidence=0.85,
    rating=None,
    flagged=False,
    reviewed=False
):
    """Create a mock chat log entry"""
    mock = MagicMock()
    mock.id = id
    mock.user_id = user_id
    mock.question = question
    mock.answer = answer
    mock.source = source
    mock.kb_entry_id = kb_entry_id
    mock.confidence = Decimal(str(confidence)) if confidence else None
    mock.rating = rating
    mock.flagged = flagged
    mock.reviewed = reviewed
    mock.reviewed_by = None
    mock.reviewed_at = None
    mock.created_at = datetime.now(timezone.utc).isoformat()
    return mock


def create_mock_db():
    """Create a mock database session"""
    mock_db = MagicMock()
    
    def mock_refresh(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 1
    
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = mock_refresh
    mock_db.execute = MagicMock()
    return mock_db


# ============================================================
# LLM Cache Tests
# ============================================================

class TestLLMCache:
    """Test LLM response caching"""

    def test_cache_set_and_get(self):
        """Test basic cache set and get"""
        cache = LLMCache(ttl_seconds=3600)
        response = LLMResponse(answer="Test answer", model="test", confidence=0.8)
        
        cache.set("test question", response)
        cached = cache.get("test question")
        
        assert cached is not None
        assert cached.answer == "Test answer"
        assert cached.cached is True

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = LLMCache(ttl_seconds=3600)
        result = cache.get("non-existent question")
        
        assert result is None

    def test_cache_with_context(self):
        """Test cache with context parameter"""
        cache = LLMCache(ttl_seconds=3600)
        response = LLMResponse(answer="Answer with context", model="test", confidence=0.7)
        
        cache.set("question", response, context="some context")
        
        # Same question, no context - should miss
        assert cache.get("question") is None
        
        # Same question, same context - should hit
        cached = cache.get("question", context="some context")
        assert cached is not None
        assert cached.answer == "Answer with context"

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = LLMCache(ttl_seconds=3600, max_entries=100)
        
        stats = cache.stats()
        assert stats["entries"] == 0
        assert stats["max_entries"] == 100
        assert stats["total_hits"] == 0

    def test_cache_clear(self):
        """Test cache clear"""
        cache = LLMCache(ttl_seconds=3600)
        response = LLMResponse(answer="Test", model="test", confidence=0.5)
        
        cache.set("q1", response)
        cache.set("q2", response)
        
        assert cache.stats()["entries"] == 2
        
        cache.clear()
        
        assert cache.stats()["entries"] == 0

    def test_cache_eviction(self):
        """Test cache evicts oldest entry when full"""
        cache = LLMCache(ttl_seconds=3600, max_entries=2)
        
        cache.set("q1", LLMResponse(answer="A1", model="test", confidence=0.5))
        cache.set("q2", LLMResponse(answer="A2", model="test", confidence=0.5))
        cache.set("q3", LLMResponse(answer="A3", model="test", confidence=0.5))
        
        # Should have evicted q1
        assert cache.stats()["entries"] == 2
        assert cache.get("q1") is None
        assert cache.get("q2") is not None


# ============================================================
# LLM Adapter Tests
# ============================================================

class TestStubAdapter:
    """Test stub LLM adapter"""

    @pytest.mark.asyncio
    async def test_stub_returns_response(self):
        """Test stub adapter returns a response"""
        adapter = StubAdapter()
        response = await adapter.generate("What's the special today?")
        
        assert response.answer is not None
        assert len(response.answer) > 0
        assert response.model in ["stub-llm-v1", "stub-local"]

    @pytest.mark.asyncio
    async def test_stub_with_cache(self):
        """Test stub adapter uses cache"""
        cache = LLMCache(ttl_seconds=3600)
        adapter = StubAdapter(cache=cache)
        
        # First call
        response1 = await adapter.generate("test question")
        assert response1.cached is False
        
        # Second call - should be cached
        response2 = await adapter.generate("test question")
        assert response2.cached is True
        assert response2.answer == response1.answer

    def test_stub_health_check(self):
        """Test stub adapter health check"""
        adapter = StubAdapter()
        health = adapter.health_check()
        
        assert health["status"] == "ok"
        assert health["adapter"] == "stub"


class TestAdapterFactory:
    """Test adapter factory function"""

    def test_get_stub_adapter(self):
        """Test getting stub adapter"""
        with patch.dict('os.environ', {'LLM_ADAPTER': 'stub'}):
            adapter = get_llm_adapter("stub")
            assert isinstance(adapter, StubAdapter)

    def test_get_ollama_adapter(self):
        """Test getting Ollama adapter"""
        adapter = get_llm_adapter("ollama")
        assert isinstance(adapter, OllamaAdapter)

    def test_default_adapter(self):
        """Test default adapter is stub"""
        with patch.dict('os.environ', {'LLM_ADAPTER': ''}):
            adapter = get_llm_adapter()
            assert isinstance(adapter, StubAdapter)


# ============================================================
# Chat Query Tests
# ============================================================

class TestChatQuery:
    """Test POST /chat/query endpoint"""

    def test_query_without_user(self):
        """Test query without user_id or authentication fails"""
        response = client.post("/chat/query", json={
            "question": "What's the special today?"
        })
        
        assert response.status_code == 400
        assert "user_id required" in response.json()["detail"]

    def test_query_kb_match(self):
        """Test query that matches KB returns KB answer"""
        mock_user = create_mock_user()
        mock_kb = create_mock_kb_entry()
        mock_chat = create_mock_chat_log()
        mock_db = create_mock_db()
        
        # Setup query chain
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Setup execute for full-text search
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            (mock_kb.id, mock_kb.question, mock_kb.answer, mock_kb.keywords,
             mock_kb.confidence, mock_kb.author_id, mock_kb.is_active,
             mock_kb.created_at, 0.8)
        ])
        mock_result.fetchone.return_value = (
            mock_kb.id, mock_kb.question, mock_kb.answer, mock_kb.keywords,
            mock_kb.confidence, mock_kb.author_id, mock_kb.is_active,
            mock_kb.created_at, 0.8
        )
        mock_db.execute.return_value = mock_result
        
        # Second query call for KB entry
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'Account':
                mock_query.filter.return_value.first.return_value = mock_user
            elif model.__name__ == 'KnowledgeBase':
                mock_query.filter.return_value.first.return_value = mock_kb
            elif model.__name__ == 'ChatLog':
                mock_query.filter.return_value.first.return_value = mock_chat
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/query", json={
                "user_id": 1,
                "question": "What are your hours?"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "kb"
            assert "hours" in data["answer"].lower() or data["answer"] == mock_kb.answer
            assert data["confidence"] > 0.5
        finally:
            app.dependency_overrides.clear()

    def test_query_llm_fallback(self):
        """Test query without KB match calls LLM"""
        mock_user = create_mock_user()
        mock_db = create_mock_db()
        
        # Setup user query to succeed
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'Account':
                mock_query.filter.return_value.first.return_value = mock_user
            else:
                mock_query.filter.return_value.first.return_value = None
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        mock_db.execute.return_value.fetchone.return_value = None  # No KB match
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock the LLM adapter
        with patch('app.routers.chat.get_llm_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.name = "stub"
            mock_adapter.generate = AsyncMock(return_value=LLMResponse(
                answer="I'd be happy to help with that!",
                model="stub",
                confidence=0.5
            ))
            mock_get_adapter.return_value = mock_adapter
            
            try:
                response = client.post("/chat/query", json={
                    "user_id": 1,
                    "question": "Something unique that won't match KB"
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["source"] == "llm"
                assert data["answer"] == "I'd be happy to help with that!"
            finally:
                app.dependency_overrides.clear()


# ============================================================
# Rating Tests
# ============================================================

class TestChatRating:
    """Test POST /chat/{chat_id}/rate endpoint"""

    def test_rate_chat_success(self):
        """Test rating a chat response"""
        mock_chat = create_mock_chat_log(id=1)
        mock_db = create_mock_db()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chat
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/1/rate", json={
                "rating": 5
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["chat_id"] == 1
            assert data["rating"] == 5
            assert data["flagged"] is False
        finally:
            app.dependency_overrides.clear()

    def test_rate_zero_flags_chat(self):
        """Test rating 0 flags the chat for review"""
        mock_chat = create_mock_chat_log(id=1, flagged=False)
        mock_db = create_mock_db()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chat
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/1/rate", json={
                "rating": 0
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["flagged"] is True
            assert "flagged" in data["message"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_rate_nonexistent_chat(self):
        """Test rating a non-existent chat fails"""
        mock_db = create_mock_db()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/999/rate", json={
                "rating": 5
            })
            
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_rate_invalid_rating(self):
        """Test invalid rating values are rejected"""
        response = client.post("/chat/1/rate", json={
            "rating": 6  # Invalid - max is 5
        })
        
        assert response.status_code == 422

        response = client.post("/chat/1/rate", json={
            "rating": -1  # Invalid - min is 0
        })
        
        assert response.status_code == 422


# ============================================================
# Manager Flagged Review Tests
# ============================================================

class TestFlaggedReview:
    """Test manager flagged chat review endpoints"""

    def test_get_flagged_requires_manager(self):
        """Test GET /chat/flagged requires manager role"""
        mock_user = create_mock_user(type="customer")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/chat/flagged")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_get_flagged_success(self):
        """Test manager can get flagged chats"""
        mock_manager = create_mock_manager()
        mock_flagged = create_mock_chat_log(id=1, flagged=True, rating=0)
        mock_user = create_mock_user()
        mock_db = create_mock_db()
        
        # Setup query chain for flagged chats and user lookup
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'ChatLog':
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 1
                mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_flagged]
            elif model.__name__ == 'Account':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/chat/flagged")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["flagged_chats"]) == 1
        finally:
            app.dependency_overrides.clear()

    def test_review_dismiss(self):
        """Test manager can dismiss flagged chat"""
        mock_manager = create_mock_manager()
        mock_flagged = create_mock_chat_log(id=1, flagged=True, rating=0)
        mock_db = create_mock_db()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_flagged
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/1/review", json={
                "action": "dismiss"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["action_taken"] == "dismiss"
            assert mock_flagged.reviewed is True
        finally:
            app.dependency_overrides.clear()

    def test_review_remove_kb(self):
        """Test manager can remove KB entry"""
        mock_manager = create_mock_manager()
        mock_kb = create_mock_kb_entry(id=5)
        mock_flagged = create_mock_chat_log(id=1, flagged=True, kb_entry_id=5)
        mock_db = create_mock_db()
        
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'ChatLog':
                mock_query.filter.return_value.first.return_value = mock_flagged
            elif model.__name__ == 'KnowledgeBase':
                mock_query.filter.return_value.first.return_value = mock_kb
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/1/review", json={
                "action": "remove_kb"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["action_taken"] == "remove_kb"
            assert data["kb_entries_affected"] == 1
            assert mock_kb.is_active is False
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Knowledge Base CRUD Tests
# ============================================================

class TestKnowledgeBaseCRUD:
    """Test KB CRUD endpoints (manager only)"""

    def test_list_kb_requires_manager(self):
        """Test listing KB requires manager"""
        mock_user = create_mock_user(type="customer")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/chat/kb")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_list_kb_success(self):
        """Test manager can list KB entries"""
        mock_manager = create_mock_manager()
        mock_kb = create_mock_kb_entry()
        mock_db = create_mock_db()
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_kb]
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/chat/kb")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["question"] == mock_kb.question
        finally:
            app.dependency_overrides.clear()

    def test_create_kb_entry(self):
        """Test manager can create KB entry"""
        mock_manager = create_mock_manager()
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/chat/kb", json={
                "question": "How do I place an order?",
                "answer": "You can order through our app or website.",
                "keywords": "order,how,place",
                "confidence": 0.9
            })
            
            assert response.status_code == 201
            data = response.json()
            assert data["question"] == "How do I place an order?"
            assert data["confidence"] == 0.9
        finally:
            app.dependency_overrides.clear()

    def test_update_kb_entry(self):
        """Test manager can update KB entry"""
        mock_manager = create_mock_manager()
        mock_kb = create_mock_kb_entry(id=1)
        mock_db = create_mock_db()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_kb
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.put("/chat/kb/1", json={
                "answer": "Updated answer",
                "confidence": 0.95
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Updated answer"
            assert data["confidence"] == 0.95
        finally:
            app.dependency_overrides.clear()

    def test_delete_kb_entry(self):
        """Test manager can soft-delete KB entry"""
        mock_manager = create_mock_manager()
        mock_kb = create_mock_kb_entry(id=1)
        mock_db = create_mock_db()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_kb
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.delete("/chat/kb/1")
            
            assert response.status_code == 204
            assert mock_kb.is_active is False
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Adapter Health/Cache Endpoints Tests
# ============================================================

class TestAdapterEndpoints:
    """Test adapter health and cache endpoints"""

    def test_adapter_health_requires_manager(self):
        """Test adapter health requires manager"""
        mock_user = create_mock_user(type="customer")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/chat/adapter/health")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_adapter_health_success(self):
        """Test manager can get adapter health"""
        mock_manager = create_mock_manager()
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        
        try:
            response = client.get("/chat/adapter/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "adapter" in data
            assert "cache" in data
        finally:
            app.dependency_overrides.clear()

    def test_clear_cache(self):
        """Test manager can clear cache"""
        mock_manager = create_mock_manager()
        
        app.dependency_overrides[get_current_user] = lambda: mock_manager
        
        try:
            response = client.post("/chat/adapter/cache/clear")
            
            assert response.status_code == 200
            assert response.json()["message"] == "Cache cleared"
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Integration Tests
# ============================================================

class TestChatFlow:
    """Integration tests for complete chat flow"""

    def test_query_rate_flow(self):
        """Test complete flow: query -> get answer -> rate"""
        mock_user = create_mock_user()
        mock_chat = create_mock_chat_log(id=1)
        mock_db = create_mock_db()
        
        # For query
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'Account':
                mock_query.filter.return_value.first.return_value = mock_user
            elif model.__name__ == 'ChatLog':
                mock_query.filter.return_value.first.return_value = mock_chat
            else:
                mock_query.filter.return_value.first.return_value = None
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        mock_db.execute.return_value.fetchone.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock LLM
        with patch('app.routers.chat.get_llm_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.name = "stub"
            mock_adapter.generate = AsyncMock(return_value=LLMResponse(
                answer="Test answer",
                model="stub",
                confidence=0.5
            ))
            mock_get_adapter.return_value = mock_adapter
            
            try:
                # Step 1: Query
                query_response = client.post("/chat/query", json={
                    "user_id": 1,
                    "question": "Test question"
                })
                
                assert query_response.status_code == 200
                chat_id = query_response.json()["chat_id"]
                
                # Step 2: Rate
                rate_response = client.post(f"/chat/{chat_id}/rate", json={
                    "rating": 4
                })
                
                assert rate_response.status_code == 200
                assert rate_response.json()["rating"] == 4
            finally:
                app.dependency_overrides.clear()

    def test_flag_and_review_flow(self):
        """Test flow: rate 0 -> flag -> manager review"""
        mock_user = create_mock_user()
        mock_manager = create_mock_manager()
        mock_chat = create_mock_chat_log(id=1, flagged=False)
        mock_db = create_mock_db()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chat
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # Step 1: Rate 0 to flag
            rate_response = client.post("/chat/1/rate", json={
                "rating": 0
            })
            
            assert rate_response.status_code == 200
            assert rate_response.json()["flagged"] is True
            
            # Update mock for review
            mock_chat.flagged = True
            
            # Step 2: Manager reviews
            app.dependency_overrides[get_current_user] = lambda: mock_manager
            
            review_response = client.post("/chat/1/review", json={
                "action": "dismiss"
            })
            
            assert review_response.status_code == 200
            assert mock_chat.reviewed is True
        finally:
            app.dependency_overrides.clear()
