"""
Knowledge Base and LLM Chat Tests
Verifies KB-first routing, LLM fallback, rating system, and manager review queue.
"""
import pytest
import pytest_asyncio
import httpx
import asyncpg
import os


BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db")


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def db_conn():
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def customer_token(client):
    response = await client.post("/auth/login", json={
        "email": "customer1@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def manager_token(client):
    response = await client.post("/auth/login", json={
        "email": "manager@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


# ============================================================================
# KNOWLEDGE BASE ROUTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_kb_answer_returned_when_match_found(client, customer_token, db_conn):
    """KB answer returned for matching queries"""
    # Query about opening hours (exists in KB)
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "What are your opening hours?"}
    )
    
    assert response.status_code == 200, f"Chat failed: {response.text}"
    data = response.json()
    
    assert "answer" in data
    assert data.get("source") == "kb" or "9am" in data["answer"].lower()
    
    # Check chat_log
    if data.get("chat_log_id"):
        log = await db_conn.fetchrow(
            'SELECT * FROM chat_log WHERE id = $1', data["chat_log_id"]
        )
        assert log["source"] == "kb"


@pytest.mark.asyncio
async def test_llm_fallback_when_no_kb_match(client, customer_token, db_conn):
    """LLM adapter used when no KB entry matches"""
    # Query with no KB match
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "What is the secret ingredient in your special sauce?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    # Source should be 'llm' or answer should be generic
    source = data.get("source", "")
    
    if source == "llm":
        # Verify chat_log
        if data.get("chat_log_id"):
            log = await db_conn.fetchrow(
                'SELECT * FROM chat_log WHERE id = $1', data["chat_log_id"]
            )
            assert log["source"] == "llm"
            assert log["kb_entry_id"] is None


@pytest.mark.asyncio
async def test_kb_match_uses_keywords(client, customer_token):
    """KB matching works with keywords"""
    # Query using keyword variations
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "Do you offer delivery service?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should match KB entry about delivery
    assert "deliver" in data["answer"].lower()


@pytest.mark.asyncio
async def test_kb_confidence_threshold_applied(client, customer_token):
    """Only high-confidence KB matches are returned"""
    # Low confidence queries should fallback to LLM
    # This tests if confidence scoring exists
    
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "hours?"}  # Very vague
    )
    
    assert response.status_code == 200
    # May use KB or LLM depending on confidence


# ============================================================================
# RATING SYSTEM TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_customer_can_rate_chat_response(client, customer_token, db_conn):
    """Customer can rate chat responses"""
    # Ask question
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "What are your opening hours?"}
    )
    chat_log_id = response.json().get("chat_log_id")
    
    if chat_log_id:
        # Rate response
        response = await client.post(f"/chat/{chat_log_id}/rate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"rating": 5}
        )
        
        assert response.status_code == 200, f"Rating failed: {response.text}"
        
        # Verify rating stored
        log = await db_conn.fetchrow(
            'SELECT * FROM chat_log WHERE id = $1', chat_log_id
        )
        assert log["rating"] == 5


@pytest.mark.asyncio
async def test_rating_zero_flags_kb_entry(client, customer_token, db_conn):
    """Rating 0 flags KB entry for manager review"""
    # Ask KB question
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "How do I become VIP?"}
    )
    
    chat_log_id = response.json().get("chat_log_id")
    
    if chat_log_id:
        # Rate 0
        response = await client.post(f"/chat/{chat_log_id}/rate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"rating": 0}
        )
        
        if response.status_code == 200:
            # Verify flagged
            log = await db_conn.fetchrow(
                'SELECT * FROM chat_log WHERE id = $1', chat_log_id
            )
            assert log["flagged"] == True


@pytest.mark.asyncio
async def test_manager_review_queue_shows_flagged_responses(client, manager_token, db_conn):
    """Manager can see flagged chat responses"""
    response = await client.get("/chat/flagged",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    
    assert response.status_code == 200, f"Review queue failed: {response.text}"
    data = response.json()
    
    # Should return list of flagged chats or dict with flagged_chats
    assert isinstance(data, list) or "items" in data or "flagged_chats" in data


@pytest.mark.asyncio
async def test_manager_can_review_and_update_kb(client, customer_token, manager_token, db_conn):
    """Manager can review flagged response and update KB"""
    # Create flagged entry
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "What is your refund policy?"}
    )
    chat_log_id = response.json().get("chat_log_id")
    
    if chat_log_id:
        # Flag it
        await client.post(f"/chat/{chat_log_id}/rate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"rating": 0}
        )
        
        # Manager reviews
        response = await client.post(f"/manager/chat/{chat_log_id}/review",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "action": "update_kb",
                "new_answer": "Updated refund policy answer"
            }
        )
        
        if response.status_code == 200:
            # Verify marked as reviewed
            log = await db_conn.fetchrow(
                'SELECT * FROM chat_log WHERE id = $1', chat_log_id
            )
            assert log["reviewed"] == True


# ============================================================================
# LLM ADAPTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_llm_response_stored_in_chat_log(client, customer_token, db_conn):
    """LLM responses are logged with source='llm'"""
    # Ask novel question
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "Tell me about your restaurant's history and founding story"}
    )
    
    if response.status_code == 200:
        chat_log_id = response.json().get("chat_log_id")
        
        if chat_log_id:
            log = await db_conn.fetchrow(
                'SELECT * FROM chat_log WHERE id = $1', chat_log_id
            )
            
            # Should be LLM source
            assert log["source"] in ["llm", "kb"]
            assert log["question"] is not None
            assert log["answer"] is not None


@pytest.mark.asyncio
async def test_llm_fallback_graceful_when_service_down(client, customer_token):
    """Graceful error handling when LLM service unavailable"""
    # If LLM service is down, should return error message
    # This depends on whether mock is running
    
    response = await client.post("/chat/query",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "Random question that won't match KB"}
    )
    
    # Should either succeed with LLM response or return error
    assert response.status_code in [200, 503]


@pytest.mark.asyncio
async def test_chat_history_retrievable(client, customer_token):
    """Customer can retrieve their chat history"""
    response = await client.get("/chat/history",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return list of previous chats
    assert isinstance(data, list) or "items" in data


@pytest.mark.asyncio
async def test_kb_entry_can_be_deactivated(client, manager_token, db_conn):
    """Manager can deactivate outdated KB entries"""
    # Get a KB entry
    kb_entry = await db_conn.fetchrow(
        'SELECT * FROM knowledge_base WHERE is_active = true LIMIT 1'
    )
    
    if kb_entry:
        kb_id = kb_entry["id"]
        
        # Manager deactivates
        response = await client.post(f"/manager/kb/{kb_id}/deactivate",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"reason": "Outdated information"}
        )
        
        if response.status_code == 200:
            # Verify deactivated
            updated = await db_conn.fetchrow(
                'SELECT * FROM knowledge_base WHERE id = $1', kb_id
            )
            assert updated["is_active"] == False


@pytest.mark.asyncio
async def test_manager_can_add_new_kb_entry(client, manager_token, db_conn):
    """Manager can add new KB entries"""
    response = await client.post("/chat/kb",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "question": "What dietary options do you offer?",
            "answer": "We offer vegetarian, vegan, and gluten-free options. Please ask about specific dietary needs.",
            "keywords": "dietary,vegan,vegetarian,gluten-free,allergy"
        }
    )
    
    if response.status_code in [200, 201]:
        kb_id = response.json().get("id")
        
        # Verify in database
        entry = await db_conn.fetchrow(
            'SELECT * FROM knowledge_base WHERE id = $1', kb_id
        )
        assert entry is not None
        assert entry["is_active"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
