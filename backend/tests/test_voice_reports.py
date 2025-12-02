"""
Tests for Voice Reports functionality
"""

import os
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from app.main import app
from app.database import Base, get_db
from app.models import Account, VoiceReport
from app.auth import create_access_token


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_voice_reports.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test db file
    if os.path.exists("test_voice_reports.db"):
        os.remove("test_voice_reports.db")


@pytest.fixture
def client(setup_database):
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def db_session(setup_database):
    """Database session fixture"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def customer_user(db_session):
    """Create a test customer user"""
    user = Account(
        ID=100,
        email="customer@test.com",
        password="hashed_password",
        type="customer",
        balance=10000,
        warnings=0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def vip_user(db_session):
    """Create a test VIP user"""
    user = Account(
        ID=101,
        email="vip@test.com",
        password="hashed_password",
        type="vip",
        balance=50000,
        warnings=0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def delivery_user(db_session):
    """Create a test delivery user"""
    user = Account(
        ID=102,
        email="delivery@test.com",
        password="hashed_password",
        type="delivery",
        balance=5000,
        warnings=0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_user(db_session):
    """Create a test manager user"""
    user = Account(
        ID=103,
        email="manager@test.com",
        password="hashed_password",
        type="manager",
        balance=0,
        warnings=0,
        restaurantID=1
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def chef_user(db_session):
    """Create a test chef user"""
    user = Account(
        ID=104,
        email="chef@test.com",
        password="hashed_password",
        type="chef",
        balance=0,
        warnings=0,
        restaurantID=1
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def customer_token(customer_user):
    """Generate JWT token for customer"""
    return create_access_token(data={"sub": customer_user.email, "user_id": customer_user.ID})


@pytest.fixture
def manager_token(manager_user):
    """Generate JWT token for manager"""
    return create_access_token(data={"sub": manager_user.email, "user_id": manager_user.ID})


@pytest.fixture
def delivery_token(delivery_user):
    """Generate JWT token for delivery user"""
    return create_access_token(data={"sub": delivery_user.email, "user_id": delivery_user.ID})


def create_test_audio_file(filename="test_audio.mp3", content=b"fake audio data"):
    """Create a fake audio file for testing"""
    return BytesIO(content)


class TestVoiceReportSubmission:
    """Tests for voice report submission endpoint"""
    
    def test_submit_voice_report_as_customer(self, client, customer_token):
        """Test customer can submit voice report"""
        audio_file = create_test_audio_file()
        
        response = client.post(
            "/voice-reports/submit",
            files={"audio_file": ("complaint.mp3", audio_file, "audio/mpeg")},
            data={},
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"]
        assert data["report_id"]
        assert data["status"] == "pending" or data["status"] == "analyzed"
        assert data["file_size_bytes"] > 0
    
    def test_submit_voice_report_with_order_id(self, client, customer_token):
        """Test submitting voice report with related order"""
        audio_file = create_test_audio_file()
        
        response = client.post(
            "/voice-reports/submit",
            files={"audio_file": ("complaint.mp3", audio_file, "audio/mpeg")},
            data={"related_order_id": 123},
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["report_id"]
    
    def test_submit_voice_report_as_delivery(self, client, delivery_token):
        """Test delivery person can submit voice report"""
        audio_file = create_test_audio_file()
        
        response = client.post(
            "/voice-reports/submit",
            files={"audio_file": ("feedback.mp3", audio_file, "audio/mpeg")},
            data={},
            headers={"Authorization": f"Bearer {delivery_token}"}
        )
        
        assert response.status_code == 200
    
    def test_submit_voice_report_invalid_format(self, client, customer_token):
        """Test submitting invalid audio format"""
        text_file = BytesIO(b"not an audio file")
        
        response = client.post(
            "/voice-reports/submit",
            files={"audio_file": ("test.txt", text_file, "text/plain")},
            data={},
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 400
        assert "Invalid audio format" in response.json()["detail"]
    
    def test_submit_voice_report_empty_file(self, client, customer_token):
        """Test submitting empty file"""
        empty_file = BytesIO(b"")
        
        response = client.post(
            "/voice-reports/submit",
            files={"audio_file": ("empty.mp3", empty_file, "audio/mpeg")},
            data={},
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]
    
    def test_submit_voice_report_unauthenticated(self, client):
        """Test submitting without authentication"""
        audio_file = create_test_audio_file()
        
        response = client.post(
            "/voice-reports/submit",
            files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")},
            data={}
        )
        
        assert response.status_code == 401


class TestManagerDashboard:
    """Tests for manager dashboard endpoint"""
    
    def test_manager_can_view_dashboard(self, client, manager_token, db_session, customer_user):
        """Test manager can access voice reports dashboard"""
        # Create a test voice report
        report = VoiceReport(
            submitter_id=customer_user.ID,
            audio_file_path="/fake/path/audio.mp3",
            file_size_bytes=1024,
            mime_type="audio/mpeg",
            transcription="This is a test complaint about the chef.",
            sentiment="complaint",
            subjects=["chef", "food"],
            auto_labels=["Complaint Chef", "Food Quality Issue"],
            confidence_score=0.85,
            status="analyzed",
            is_processed=True,
            created_at="2025-12-02T10:00:00Z",
            updated_at="2025-12-02T10:05:00Z"
        )
        db_session.add(report)
        db_session.commit()
        
        response = client.get(
            "/voice-reports/manager/dashboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data
        assert "pending_count" in data
        assert "unresolved_complaints" in data
        assert len(data["reports"]) > 0
        
        # Check first report structure
        first_report = data["reports"][0]
        assert "transcription" in first_report
        assert "sentiment" in first_report
        assert "auto_labels" in first_report
        assert "audio_url" in first_report
    
    def test_manager_filter_by_sentiment(self, client, manager_token, db_session, customer_user):
        """Test filtering reports by sentiment"""
        # Create reports with different sentiments
        for sentiment in ["complaint", "compliment", "neutral"]:
            report = VoiceReport(
                submitter_id=customer_user.ID,
                audio_file_path=f"/fake/{sentiment}.mp3",
                file_size_bytes=1024,
                mime_type="audio/mpeg",
                sentiment=sentiment,
                status="analyzed",
                is_processed=True,
                created_at="2025-12-02T10:00:00Z",
                updated_at="2025-12-02T10:00:00Z"
            )
            db_session.add(report)
        db_session.commit()
        
        response = client.get(
            "/voice-reports/manager/dashboard?sentiment=complaint",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for report in data["reports"]:
            assert report["sentiment"] == "complaint"
    
    def test_non_manager_cannot_view_dashboard(self, client, customer_token):
        """Test non-manager cannot access dashboard"""
        response = client.get(
            "/voice-reports/manager/dashboard",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 403


class TestAudioStreaming:
    """Tests for audio file streaming endpoint"""
    
    def test_submitter_can_access_own_audio(self, client, customer_token, db_session, customer_user):
        """Test user can access their own audio files"""
        # Create temp audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(b"fake audio data")
            tmp_path = tmp.name
        
        try:
            # Create voice report
            report = VoiceReport(
                submitter_id=customer_user.ID,
                audio_file_path=tmp_path,
                file_size_bytes=15,
                mime_type="audio/mpeg",
                status="pending",
                is_processed=False,
                created_at="2025-12-02T10:00:00Z",
                updated_at="2025-12-02T10:00:00Z"
            )
            db_session.add(report)
            db_session.commit()
            db_session.refresh(report)
            
            response = client.get(
                f"/voice-reports/audio/{report.id}",
                headers={"Authorization": f"Bearer {customer_token}"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"
        
        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def test_manager_can_access_any_audio(self, client, manager_token, db_session, customer_user):
        """Test manager can access any audio file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(b"fake audio data")
            tmp_path = tmp.name
        
        try:
            report = VoiceReport(
                submitter_id=customer_user.ID,
                audio_file_path=tmp_path,
                file_size_bytes=15,
                mime_type="audio/mpeg",
                status="pending",
                is_processed=False,
                created_at="2025-12-02T10:00:00Z",
                updated_at="2025-12-02T10:00:00Z"
            )
            db_session.add(report)
            db_session.commit()
            db_session.refresh(report)
            
            response = client.get(
                f"/voice-reports/audio/{report.id}",
                headers={"Authorization": f"Bearer {manager_token}"}
            )
            
            assert response.status_code == 200
        
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def test_cannot_access_others_audio(self, client, delivery_token, db_session, customer_user):
        """Test user cannot access other users' audio"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(b"fake audio data")
            tmp_path = tmp.name
        
        try:
            report = VoiceReport(
                submitter_id=customer_user.ID,
                audio_file_path=tmp_path,
                file_size_bytes=15,
                mime_type="audio/mpeg",
                status="pending",
                is_processed=False,
                created_at="2025-12-02T10:00:00Z",
                updated_at="2025-12-02T10:00:00Z"
            )
            db_session.add(report)
            db_session.commit()
            db_session.refresh(report)
            
            response = client.get(
                f"/voice-reports/audio/{report.id}",
                headers={"Authorization": f"Bearer {delivery_token}"}
            )
            
            assert response.status_code == 403
        
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestResolveVoiceReport:
    """Tests for resolving voice reports"""
    
    def test_manager_can_dismiss_report(self, client, manager_token, db_session, customer_user):
        """Test manager can dismiss a report"""
        report = VoiceReport(
            submitter_id=customer_user.ID,
            audio_file_path="/fake/path.mp3",
            file_size_bytes=1024,
            mime_type="audio/mpeg",
            sentiment="neutral",
            status="analyzed",
            is_processed=True,
            created_at="2025-12-02T10:00:00Z",
            updated_at="2025-12-02T10:00:00Z"
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        
        response = client.post(
            f"/voice-reports/{report.id}/resolve",
            json={"action": "dismiss", "notes": "Not actionable"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action_taken"] == "dismiss"
        assert data["resolved_at"]
    
    def test_manager_can_issue_warning(self, client, manager_token, db_session, customer_user, chef_user):
        """Test manager can issue warning from voice report"""
        report = VoiceReport(
            submitter_id=customer_user.ID,
            audio_file_path="/fake/path.mp3",
            file_size_bytes=1024,
            mime_type="audio/mpeg",
            transcription="The chef was rude and unprofessional",
            sentiment="complaint",
            subjects=["chef"],
            auto_labels=["Complaint Chef"],
            status="analyzed",
            is_processed=True,
            created_at="2025-12-02T10:00:00Z",
            updated_at="2025-12-02T10:00:00Z"
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        
        initial_warnings = chef_user.warnings
        
        response = client.post(
            f"/voice-reports/{report.id}/resolve",
            json={
                "action": "warning",
                "related_account_id": chef_user.ID,
                "notes": "Valid complaint, warning issued"
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["warning_applied"] is True
        
        # Verify warning was applied
        db_session.refresh(chef_user)
        assert chef_user.warnings == initial_warnings + 1
    
    def test_manager_can_create_formal_complaint(self, client, manager_token, db_session, customer_user, chef_user):
        """Test manager can refer voice report to formal complaint"""
        report = VoiceReport(
            submitter_id=customer_user.ID,
            audio_file_path="/fake/path.mp3",
            file_size_bytes=1024,
            mime_type="audio/mpeg",
            transcription="Serious issue with food safety",
            sentiment="complaint",
            subjects=["chef", "food"],
            status="analyzed",
            is_processed=True,
            created_at="2025-12-02T10:00:00Z",
            updated_at="2025-12-02T10:00:00Z"
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        
        response = client.post(
            f"/voice-reports/{report.id}/resolve",
            json={
                "action": "refer_to_complaint",
                "related_account_id": chef_user.ID,
                "notes": "Serious issue requiring formal complaint"
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["complaint_created_id"] is not None
    
    def test_non_manager_cannot_resolve(self, client, customer_token, db_session, customer_user):
        """Test non-manager cannot resolve reports"""
        report = VoiceReport(
            submitter_id=customer_user.ID,
            audio_file_path="/fake/path.mp3",
            file_size_bytes=1024,
            mime_type="audio/mpeg",
            status="analyzed",
            is_processed=True,
            created_at="2025-12-02T10:00:00Z",
            updated_at="2025-12-02T10:00:00Z"
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        
        response = client.post(
            f"/voice-reports/{report.id}/resolve",
            json={"action": "dismiss"},
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 403


class TestMyReports:
    """Tests for user's own reports endpoint"""
    
    def test_user_can_view_own_reports(self, client, customer_token, db_session, customer_user):
        """Test user can view their own reports"""
        # Create reports for this user
        for i in range(3):
            report = VoiceReport(
                submitter_id=customer_user.ID,
                audio_file_path=f"/fake/path{i}.mp3",
                file_size_bytes=1024,
                mime_type="audio/mpeg",
                status="analyzed",
                is_processed=True,
                created_at=f"2025-12-02T10:{i:02d}:00Z",
                updated_at=f"2025-12-02T10:{i:02d}:00Z"
            )
            db_session.add(report)
        db_session.commit()
        
        response = client.get(
            "/voice-reports/my-reports",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert len(data["reports"]) >= 3
        
        # All reports should belong to this user
        for report in data["reports"]:
            assert report["submitter_id"] == customer_user.ID


class TestNLPAnalysis:
    """Tests for NLP analysis functionality"""
    
    def test_complaint_detection(self):
        """Test NLP correctly detects complaints"""
        from app.voice_report_nlp import get_nlp_analyzer
        
        analyzer = get_nlp_analyzer(use_advanced_nlp=False)
        text = "I have a complaint about the terrible service and cold food"
        
        result = analyzer.analyze_report(text)
        
        assert result["sentiment"] == "complaint"
        assert result["confidence"] > 0.5
        assert "food" in result["subjects"]
    
    def test_compliment_detection(self):
        """Test NLP correctly detects compliments"""
        from app.voice_report_nlp import get_nlp_analyzer
        
        analyzer = get_nlp_analyzer(use_advanced_nlp=False)
        text = "The chef did an excellent job, the food was amazing and delicious"
        
        result = analyzer.analyze_report(text)
        
        assert result["sentiment"] == "compliment"
        assert "chef" in result["subjects"]
        assert any("Compliment" in label for label in result["auto_labels"])
    
    def test_subject_extraction(self):
        """Test NLP extracts correct subjects"""
        from app.voice_report_nlp import get_nlp_analyzer
        
        analyzer = get_nlp_analyzer(use_advanced_nlp=False)
        text = "The driver was late and the chef made the food poorly"
        
        result = analyzer.analyze_report(text)
        
        assert "driver" in result["subjects"]
        assert "chef" in result["subjects"]
    
    def test_auto_label_generation(self):
        """Test auto-label generation"""
        from app.voice_report_nlp import get_nlp_analyzer
        
        analyzer = get_nlp_analyzer(use_advanced_nlp=False)
        text = "Complaint about the delivery person being unprofessional"
        
        result = analyzer.analyze_report(text)
        
        assert "Complaint Delivery Person" in result["auto_labels"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
