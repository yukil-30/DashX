"""
Audio Transcription Adapter
Provides audio-to-text transcription using local models or stub fallback
"""

import logging
from typing import Optional, Tuple
import os

logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """
    Audio transcription service with local model support
    
    In production, this can use:
    - OpenAI Whisper (local via transformers)
    - Faster Whisper (optimized local model)
    - External API (if cloud services are later enabled)
    
    For development, provides a stub that extracts basic metadata
    """
    
    def __init__(self, use_stub: bool = True):
        """
        Initialize transcription service
        
        Args:
            use_stub: If True, use stub implementation. If False, attempt to load Whisper model
        """
        self.use_stub = use_stub
        self.model = None
        
        if not use_stub:
            try:
                # Attempt to load Whisper model (requires: pip install openai-whisper)
                import whisper
                self.model = whisper.load_model("base")
                logger.info("Whisper model loaded successfully")
            except ImportError:
                logger.warning("Whisper not installed, falling back to stub. Install with: pip install openai-whisper")
                self.use_stub = True
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}, falling back to stub")
                self.use_stub = True
    
    def transcribe_audio(self, audio_file_path: str) -> Tuple[Optional[str], Optional[float], Optional[int]]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Tuple of (transcription_text, confidence_score, duration_seconds)
        """
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None, None, None
        
        if self.use_stub:
            return self._stub_transcribe(audio_file_path)
        else:
            return self._whisper_transcribe(audio_file_path)
    
    def _stub_transcribe(self, audio_file_path: str) -> Tuple[str, float, Optional[int]]:
        """
        Stub transcription for development/testing
        Returns sample transcription based on filename patterns
        """
        filename = os.path.basename(audio_file_path).lower()
        
        # Simulate different types of reports based on filename
        if 'complaint' in filename or 'issue' in filename:
            transcription = (
                "I want to file a complaint about my recent order. "
                "The chef prepared the food poorly and it arrived cold. "
                "The delivery person was also very late, over 45 minutes past the estimated time. "
                "This is unacceptable service and I demand a refund."
            )
        elif 'compliment' in filename or 'praise' in filename:
            transcription = (
                "I just wanted to say the chef did an amazing job with my order today. "
                "Everything was perfectly cooked and seasoned. "
                "The delivery person was also very professional and arrived right on time. "
                "Keep up the great work!"
            )
        elif 'late' in filename or 'delay' in filename:
            transcription = (
                "My order was delayed by over an hour. "
                "The driver said they got lost and had trouble finding my address. "
                "I understand mistakes happen, but this was really disappointing."
            )
        elif 'quality' in filename or 'food' in filename:
            transcription = (
                "The food quality was excellent today. "
                "The chef really knows how to prepare authentic dishes. "
                "I'll definitely be ordering again soon."
            )
        else:
            # Default neutral transcription
            transcription = (
                "I wanted to provide feedback about my recent experience. "
                "The staff were helpful and the service was adequate. "
                "Thank you for your attention to this matter."
            )
        
        # Simulate confidence score (stub always has decent confidence)
        confidence = 0.85
        
        # Simulate duration (estimate ~3 words per second)
        word_count = len(transcription.split())
        duration_seconds = int(word_count / 3)
        
        logger.info(f"[STUB] Transcribed audio: {len(transcription)} chars, {duration_seconds}s")
        return transcription, confidence, duration_seconds
    
    def _whisper_transcribe(self, audio_file_path: str) -> Tuple[Optional[str], Optional[float], Optional[int]]:
        """
        Real transcription using Whisper model
        """
        try:
            import whisper
            
            # Transcribe audio
            result = self.model.transcribe(audio_file_path)
            
            transcription = result.get("text", "").strip()
            
            # Whisper doesn't provide direct confidence, but we can use segment confidence
            segments = result.get("segments", [])
            if segments:
                # Average confidence across segments
                confidences = [seg.get("no_speech_prob", 0) for seg in segments]
                # no_speech_prob is inverted (lower is better), so invert it
                avg_confidence = 1.0 - (sum(confidences) / len(confidences))
            else:
                avg_confidence = 0.5  # Unknown confidence
            
            # Calculate duration from segments
            if segments:
                duration_seconds = int(segments[-1].get("end", 0))
            else:
                duration_seconds = None
            
            logger.info(f"[WHISPER] Transcribed audio: {len(transcription)} chars, {duration_seconds}s")
            return transcription, avg_confidence, duration_seconds
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None, None, None
    
    def get_audio_duration(self, audio_file_path: str) -> Optional[int]:
        """
        Get duration of audio file in seconds
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Duration in seconds, or None if unable to determine
        """
        try:
            # Try using pydub if available
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_file_path)
            return int(audio.duration_seconds)
        except ImportError:
            logger.warning("pydub not installed, cannot determine audio duration")
            return None
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return None


# Singleton instance
_transcription_service: Optional[AudioTranscriptionService] = None


def get_transcription_service(use_stub: bool = True) -> AudioTranscriptionService:
    """
    Get or create singleton transcription service instance
    
    Args:
        use_stub: Whether to use stub implementation (default True for local dev)
    """
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = AudioTranscriptionService(use_stub=use_stub)
    return _transcription_service
