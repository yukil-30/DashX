"""
Mock Speech-to-Text Server for Testing
Simulates audio transcription without requiring actual STT service.
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Mock STT Server")


class TranscriptionResponse(BaseModel):
    transcription: str
    confidence: float
    duration_seconds: float
    language: str = "en-US"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-stt"}


@app.post("/v1/transcribe", response_model=TranscriptionResponse)
async def transcribe(audio: UploadFile = File(...)):
    """Mock transcription endpoint"""
    
    # Read file to get size (simulate processing)
    contents = await audio.read()
    file_size = len(contents)
    
    # Generate mock transcription based on filename or size
    filename = audio.filename.lower() if audio.filename else ""
    
    if "complaint" in filename:
        transcription = "I want to file a complaint about the chef. The food was cold and took forever to arrive. The delivery person was also rude. This is unacceptable service."
    elif "compliment" in filename:
        transcription = "I'd like to compliment the chef and delivery person. The food was absolutely delicious and arrived hot. The delivery person was very polite and professional. Great service!"
    elif "neutral" in filename:
        transcription = "I wanted to ask about the VIP program. How do I become a VIP member and what are the benefits? Also, what are your opening hours?"
    else:
        # Default mock transcription
        transcription = "This is a test voice report. The quality of service needs improvement. Please review this matter promptly."
    
    # Estimate duration based on file size (rough approximation)
    estimated_duration = max(3.0, file_size / 10000)
    
    return TranscriptionResponse(
        transcription=transcription,
        confidence=0.92,
        duration_seconds=estimated_duration
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
