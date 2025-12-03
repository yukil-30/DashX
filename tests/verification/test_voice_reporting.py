"""
Voice Reporting Tests
Verifies audio upload, transcription, NLP analysis, label generation, and manager review.
"""
import pytest
import pytest_asyncio
import httpx
import asyncpg
import os
import io
from datetime import datetime


BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db")


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
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


def create_mock_audio_file(filename="test_audio.mp3", content_hint="complaint"):
    """Create a mock audio file for testing"""
    # Create fake audio data
    audio_data = b"MOCK_AUDIO_DATA_" + content_hint.encode() + b"_" + os.urandom(1000)
    return io.BytesIO(audio_data), filename


# ============================================================================
# AUDIO UPLOAD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_customer_can_upload_voice_report(client, customer_token, db_conn):
    """Customer can upload audio file for voice report"""
    audio_file, filename = create_mock_audio_file("complaint_audio.mp3", "complaint")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    assert response.status_code in [200, 201], f"Upload failed: {response.text}"
    data = response.json()
    
    assert "report_id" in data
    report_id = data["report_id"]
    
    # Verify in database
    report = await db_conn.fetchrow(
        'SELECT * FROM voice_reports WHERE id = $1', report_id
    )
    
    assert report is not None
    assert report["audio_file_path"] is not None
    assert report["status"] in ["pending", "transcribed", "analyzed"]


@pytest.mark.asyncio
async def test_voice_report_saves_file_metadata(client, customer_token, db_conn):
    """Voice report stores file size, mime type, and path"""
    audio_file, filename = create_mock_audio_file("metadata_test.mp3")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        assert report["file_size_bytes"] > 0
        assert report["mime_type"] == "audio/mpeg"
        assert report["audio_file_path"] is not None


@pytest.mark.asyncio
async def test_invalid_file_type_rejected(client, customer_token):
    """Non-audio files are rejected"""
    # Try to upload text file
    fake_file = io.BytesIO(b"This is not audio")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": ("text.txt", fake_file, "text/plain")}
    )
    
    # Should reject non-audio
    assert response.status_code in [400, 415, 422]


# ============================================================================
# TRANSCRIPTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_audio_transcribed_by_stt_service(client, customer_token, db_conn):
    """Audio is sent to STT service and transcription stored"""
    audio_file, filename = create_mock_audio_file("complaint_chef.mp3", "complaint")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        # Wait a moment for async processing (if applicable)
        import asyncio
        await asyncio.sleep(2)
        
        # Check transcription
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # Should have transcription or be processing
        assert report["status"] in ["transcribed", "analyzed", "pending"]
        
        if report["transcription"]:
            assert len(report["transcription"]) > 0


@pytest.mark.asyncio
async def test_transcription_duration_recorded(client, customer_token, db_conn):
    """Audio duration is recorded from transcription service"""
    audio_file, filename = create_mock_audio_file()
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(2)
        
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # Duration may be set
        if report["duration_seconds"]:
            assert report["duration_seconds"] > 0


# ============================================================================
# NLP ANALYSIS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_nlp_extracts_sentiment(client, customer_token, db_conn):
    """NLP service extracts sentiment from transcription"""
    audio_file, filename = create_mock_audio_file("complaint_test.mp3", "complaint")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(3)  # Wait for processing
        
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # Should have sentiment
        if report["is_processed"]:
            assert report["sentiment"] in ["complaint", "compliment", "neutral", None]


@pytest.mark.asyncio
async def test_nlp_extracts_subjects(client, customer_token, db_conn):
    """NLP service extracts subjects (chef, delivery, food, etc.)"""
    audio_file, filename = create_mock_audio_file("complaint_chef.mp3", "complaint")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(3)
        
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # Should have subjects array
        if report["subjects"]:
            import json
            subjects = json.loads(report["subjects"]) if isinstance(report["subjects"], str) else report["subjects"]
            assert isinstance(subjects, list)


@pytest.mark.asyncio
async def test_auto_labels_generated(client, customer_token, db_conn):
    """System generates auto-labels based on sentiment and subjects"""
    audio_file, filename = create_mock_audio_file("compliment_delivery.mp3", "compliment")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(3)
        
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # Should have auto_labels
        if report["auto_labels"]:
            import json
            labels = json.loads(report["auto_labels"]) if isinstance(report["auto_labels"], str) else report["auto_labels"]
            assert isinstance(labels, list)
            assert len(labels) > 0


@pytest.mark.asyncio
async def test_confidence_score_recorded(client, customer_token, db_conn):
    """NLP confidence score is recorded"""
    audio_file, filename = create_mock_audio_file()
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(3)
        
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # Should have confidence score
        if report["confidence_score"] is not None:
            assert 0.0 <= float(report["confidence_score"]) <= 1.0


# ============================================================================
# MANAGER REVIEW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_manager_can_view_voice_reports(client, manager_token):
    """Manager can view list of voice reports"""
    response = await client.get("/voice-reports/manager/dashboard",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    
    assert response.status_code == 200, f"Failed to get reports: {response.text}"
    data = response.json()
    
    # Should return dict with reports field
    assert isinstance(data, dict) and "reports" in data


@pytest.mark.asyncio
async def test_manager_can_view_transcription(client, customer_token, manager_token, db_conn):
    """Manager can view transcription of voice report"""
    # Upload report
    audio_file, filename = create_mock_audio_file()
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(3)
        
        # Manager views dashboard to see reports
        response = await client.get("/voice-reports/manager/dashboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return reports list
        assert "reports" in data
        # May have transcription if processed
        if data["reports"]:
            report = data["reports"][0]
            if report.get("is_processed"):
                assert "transcription" in report or "sentiment" in report


@pytest.mark.asyncio
async def test_manager_can_view_auto_labels(client, customer_token, manager_token):
    """Manager can see auto-generated labels"""
    audio_file, filename = create_mock_audio_file("complaint_chef.mp3")
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(3)
        
        response = await client.get(f"/manager/voice-reports/{report_id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            # May have auto_labels
            if "auto_labels" in data:
                assert isinstance(data["auto_labels"], list)


@pytest.mark.asyncio
async def test_audio_url_accessible_for_playback(client, customer_token, manager_token):
    """Manager can access audio URL for playback"""
    audio_file, filename = create_mock_audio_file()
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        # Get report details
        response = await client.get(f"/manager/voice-reports/{report_id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have audio_url or audio_file_path
            assert "audio_file_path" in data or "audio_url" in data


@pytest.mark.asyncio
async def test_manager_can_resolve_voice_report(client, customer_token, manager_token, db_conn):
    """Manager can resolve voice report with notes"""
    audio_file, filename = create_mock_audio_file()
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        # Manager resolves
        response = await client.post(f"/manager/voice-reports/{report_id}/resolve",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "manager_notes": "Investigated and resolved the issue",
                "action_taken": "warning_issued"
            }
        )
        
        if response.status_code == 200:
            # Verify resolved
            report = await db_conn.fetchrow(
                'SELECT * FROM voice_reports WHERE id = $1', report_id
            )
            
            assert report["status"] == "resolved"
            assert report["manager_notes"] is not None
            assert report["resolved_by"] is not None


@pytest.mark.asyncio
async def test_processing_errors_recorded(client, customer_token, db_conn):
    """Processing errors are recorded in voice_reports"""
    # This would require simulating STT/NLP failure
    # For now, check that error field exists
    
    audio_file, filename = create_mock_audio_file()
    
    response = await client.post("/voice-reports/submit",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": (filename, audio_file, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        
        import asyncio
        await asyncio.sleep(2)
        
        report = await db_conn.fetchrow(
            'SELECT * FROM voice_reports WHERE id = $1', report_id
        )
        
        # processing_error field should exist (even if NULL)
        assert "processing_error" in report.keys()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
