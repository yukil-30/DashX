"""
Voice Reports Router
Endpoints for voice-based complaint/compliment system
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth import get_current_user
from app.models import Account, VoiceReport, Complaint
from app.schemas import (
    VoiceReportSubmitResponse,
    VoiceReportResponse,
    VoiceReportListResponse,
    VoiceReportResolveRequest,
    VoiceReportResolveResponse
)
from app.background_tasks import process_voice_report_immediate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice-reports", tags=["Voice Reports"])


# Audio file configuration
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",  # .mp3
    "audio/wav",   # .wav
    "audio/mp4",   # .m4a
    "audio/x-m4a", # .m4a
    "audio/ogg",   # .ogg
    "audio/webm",  # .webm
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
AUDIO_STORAGE_DIR = Path("backend/static/voice_reports")


def get_iso_now() -> str:
    """Get current timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def ensure_audio_storage_dir():
    """Ensure audio storage directory exists"""
    AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def validate_audio_file(file: UploadFile) -> None:
    """
    Validate uploaded audio file
    
    Raises:
        HTTPException if validation fails
    """
    # Check MIME type
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio format. Allowed types: {', '.join(ALLOWED_AUDIO_TYPES)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f} MB"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")


@router.post("/submit", response_model=VoiceReportSubmitResponse)
async def submit_voice_report(
    audio_file: UploadFile = File(..., description="Audio file (mp3, wav, m4a, ogg, webm)"),
    related_order_id: Optional[int] = Form(None, description="Related order ID (optional)"),
    related_account_id: Optional[int] = Form(None, description="Account ID being reported about (optional)"),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a voice complaint or compliment.
    
    Allowed roles: customer, vip, delivery
    
    The audio will be automatically transcribed and analyzed.
    """
    # Role validation
    if current_user.type not in ["customer", "vip", "delivery"]:
        raise HTTPException(
            status_code=403,
            detail="Only customers, VIP customers, and delivery people can submit voice reports"
        )
    
    # Validate audio file
    validate_audio_file(audio_file)
    
    # Ensure storage directory exists
    ensure_audio_storage_dir()
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = Path(audio_file.filename).suffix or ".mp3"
    filename = f"voice_{current_user.ID}_{timestamp}{file_extension}"
    file_path = AUDIO_STORAGE_DIR / filename
    
    # Save audio file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        file_size = file_path.stat().st_size
        logger.info(f"Saved audio file: {file_path} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"Failed to save audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save audio file")
    
    # Create voice report record
    voice_report = VoiceReport(
        submitter_id=current_user.ID,
        audio_file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type=audio_file.content_type,
        status="pending",
        is_processed=False,
        related_order_id=related_order_id,
        related_account_id=related_account_id,
        created_at=get_iso_now(),
        updated_at=get_iso_now()
    )
    
    db.add(voice_report)
    db.commit()
    db.refresh(voice_report)
    
    logger.info(f"Created voice report {voice_report.id} from user {current_user.ID}")
    
    # Process immediately in development (in production, background task will pick it up)
    try:
        process_voice_report_immediate(voice_report.id)
        logger.info(f"Voice report {voice_report.id} processed immediately")
    except Exception as e:
        logger.warning(f"Immediate processing failed for report {voice_report.id}: {e}")
        # Not critical - background task will retry
    
    return VoiceReportSubmitResponse(
        message="Voice report submitted successfully. Processing will begin shortly.",
        report_id=voice_report.id,
        status=voice_report.status,
        audio_file_path=str(file_path),
        file_size_bytes=file_size
    )


@router.get("/manager/dashboard", response_model=VoiceReportListResponse)
async def get_voice_reports_dashboard(
    status: Optional[str] = Query(None, description="Filter by status (pending, transcribed, analyzed, resolved, error)"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (complaint, compliment, neutral)"),
    unresolved_only: bool = Query(False, description="Show only unresolved reports"),
    limit: int = Query(50, ge=1, le=200, description="Number of reports to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manager dashboard: View all voice reports with full details.
    
    Only accessible to managers.
    
    Returns:
    - Full transcription text
    - Auto-generated labels
    - Sentiment analysis
    - Direct link to audio file
    """
    # Role validation
    if current_user.type != "manager":
        raise HTTPException(status_code=403, detail="Only managers can access voice reports dashboard")
    
    # Build query
    query = db.query(VoiceReport)
    
    # Apply filters
    if status:
        query = query.filter(VoiceReport.status == status)
    
    if sentiment:
        query = query.filter(VoiceReport.sentiment == sentiment)
    
    if unresolved_only:
        query = query.filter(VoiceReport.resolved_at == None)
    
    # Get total count
    total = query.count()
    
    # Count pending and unresolved complaints
    pending_count = db.query(VoiceReport).filter(VoiceReport.status == "pending").count()
    unresolved_complaints = db.query(VoiceReport).filter(
        VoiceReport.sentiment == "complaint",
        VoiceReport.resolved_at == None
    ).count()
    
    # Get paginated results
    reports = query.order_by(desc(VoiceReport.created_at)).offset(offset).limit(limit).all()
    
    # Build response with enriched data
    report_responses = []
    for report in reports:
        # Get submitter info
        submitter = db.query(Account).filter(Account.ID == report.submitter_id).first()
        submitter_email = submitter.email if submitter else None
        submitter_type = submitter.type if submitter else None
        
        # Get related account info
        related_account_email = None
        if report.related_account_id:
            related_account = db.query(Account).filter(Account.ID == report.related_account_id).first()
            related_account_email = related_account.email if related_account else None
        
        # Build audio URL for streaming/download
        audio_url = f"/voice-reports/audio/{report.id}"
        
        report_responses.append(VoiceReportResponse(
            id=report.id,
            submitter_id=report.submitter_id,
            submitter_email=submitter_email,
            submitter_type=submitter_type,
            audio_file_path=report.audio_file_path,
            audio_url=audio_url,
            file_size_bytes=report.file_size_bytes,
            duration_seconds=report.duration_seconds,
            mime_type=report.mime_type,
            transcription=report.transcription,
            sentiment=report.sentiment,
            subjects=report.subjects,
            auto_labels=report.auto_labels,
            confidence_score=float(report.confidence_score) if report.confidence_score else None,
            status=report.status,
            is_processed=report.is_processed,
            related_order_id=report.related_order_id,
            related_account_id=report.related_account_id,
            related_account_email=related_account_email,
            processing_error=report.processing_error,
            manager_notes=report.manager_notes,
            resolved_by=report.resolved_by,
            resolved_at=report.resolved_at,
            created_at=report.created_at,
            updated_at=report.updated_at
        ))
    
    return VoiceReportListResponse(
        reports=report_responses,
        total=total,
        pending_count=pending_count,
        unresolved_complaints=unresolved_complaints
    )


@router.get("/audio/{report_id}")
async def stream_audio_file(
    report_id: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream or download audio file for a voice report.
    
    Accessible to:
    - The submitter (own reports)
    - Managers (all reports)
    """
    # Get report
    report = db.query(VoiceReport).filter(VoiceReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Voice report not found")
    
    # Access control
    if current_user.type != "manager" and current_user.ID != report.submitter_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own voice reports"
        )
    
    # Check if file exists
    file_path = Path(report.audio_file_path)
    if not file_path.exists():
        logger.error(f"Audio file not found: {file_path}")
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Return file
    return FileResponse(
        path=file_path,
        media_type=report.mime_type,
        filename=file_path.name
    )


@router.post("/{report_id}/resolve", response_model=VoiceReportResolveResponse)
async def resolve_voice_report(
    report_id: int,
    resolve_request: VoiceReportResolveRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve a voice report.
    
    Only accessible to managers.
    
    Actions:
    - dismiss: Mark as resolved without action
    - warning: Issue warning to related account
    - refer_to_complaint: Create formal complaint record
    """
    # Role validation
    if current_user.type != "manager":
        raise HTTPException(status_code=403, detail="Only managers can resolve voice reports")
    
    # Get report
    report = db.query(VoiceReport).filter(VoiceReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Voice report not found")
    
    if report.resolved_at:
        raise HTTPException(status_code=400, detail="Report already resolved")
    
    # Validate action-specific requirements
    if resolve_request.action == "warning" and not resolve_request.related_account_id:
        raise HTTPException(
            status_code=400,
            detail="related_account_id is required when issuing a warning"
        )
    
    warning_applied = False
    complaint_created_id = None
    
    # Execute action
    if resolve_request.action == "dismiss":
        # Simply mark as resolved
        pass
    
    elif resolve_request.action == "warning":
        # Issue warning to related account
        related_account = db.query(Account).filter(
            Account.ID == resolve_request.related_account_id
        ).first()
        
        if not related_account:
            raise HTTPException(status_code=404, detail="Related account not found")
        
        related_account.warnings += 1
        warning_applied = True
        
        # Update report with related account
        report.related_account_id = resolve_request.related_account_id
        
        logger.info(
            f"Issued warning to account {related_account.ID} "
            f"(total: {related_account.warnings}) from voice report {report_id}"
        )
    
    elif resolve_request.action == "refer_to_complaint":
        # Create formal complaint
        complaint = Complaint(
            accountID=resolve_request.related_account_id,
            type="complaint",
            description=f"[FROM VOICE REPORT] {report.transcription or 'No transcription available'}",
            filer=report.submitter_id,
            order_id=report.related_order_id,
            status="pending",
            created_at=get_iso_now()
        )
        db.add(complaint)
        db.flush()
        complaint_created_id = complaint.id
        
        logger.info(f"Created complaint {complaint_created_id} from voice report {report_id}")
    
    # Update voice report
    report.manager_notes = resolve_request.notes
    report.resolved_by = current_user.ID
    report.resolved_at = get_iso_now()
    report.status = "resolved"
    report.updated_at = get_iso_now()
    
    db.commit()
    
    return VoiceReportResolveResponse(
        message=f"Voice report resolved with action: {resolve_request.action}",
        report_id=report_id,
        action_taken=resolve_request.action,
        warning_applied=warning_applied,
        complaint_created_id=complaint_created_id,
        resolved_at=report.resolved_at
    )


@router.get("/my-reports", response_model=VoiceReportListResponse)
async def get_my_voice_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice reports submitted by the current user.
    
    Accessible to all authenticated users.
    """
    # Build query for current user's reports
    query = db.query(VoiceReport).filter(VoiceReport.submitter_id == current_user.ID)
    
    total = query.count()
    reports = query.order_by(desc(VoiceReport.created_at)).offset(offset).limit(limit).all()
    
    # Build response
    report_responses = []
    for report in reports:
        audio_url = f"/voice-reports/audio/{report.id}"
        
        report_responses.append(VoiceReportResponse(
            id=report.id,
            submitter_id=report.submitter_id,
            submitter_email=current_user.email,
            submitter_type=current_user.type,
            audio_file_path=report.audio_file_path,
            audio_url=audio_url,
            file_size_bytes=report.file_size_bytes,
            duration_seconds=report.duration_seconds,
            mime_type=report.mime_type,
            transcription=report.transcription,
            sentiment=report.sentiment,
            subjects=report.subjects,
            auto_labels=report.auto_labels,
            confidence_score=float(report.confidence_score) if report.confidence_score else None,
            status=report.status,
            is_processed=report.is_processed,
            related_order_id=report.related_order_id,
            related_account_id=report.related_account_id,
            processing_error=report.processing_error,
            manager_notes=report.manager_notes,
            resolved_by=report.resolved_by,
            resolved_at=report.resolved_at,
            created_at=report.created_at,
            updated_at=report.updated_at
        ))
    
    return VoiceReportListResponse(
        reports=report_responses,
        total=total,
        pending_count=0,  # Not applicable for user view
        unresolved_complaints=0  # Not applicable for user view
    )
