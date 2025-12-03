"""
Mock NLP Analysis Server for Testing
Simulates sentiment and subject extraction from text.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Mock NLP Server")


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    sentiment: str  # complaint, compliment, neutral
    subjects: List[str]  # ["chef", "delivery", "food", "service"]
    confidence: float
    auto_labels: List[str]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-nlp"}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """Mock NLP analysis endpoint"""
    text = request.text.lower()
    
    # Sentiment detection
    complaint_keywords = ["complaint", "problem", "issue", "bad", "terrible", "awful", "poor", "unacceptable", "rude", "cold", "late"]
    compliment_keywords = ["compliment", "great", "excellent", "wonderful", "amazing", "perfect", "delicious", "polite", "professional", "thank"]
    
    complaint_count = sum(1 for word in complaint_keywords if word in text)
    compliment_count = sum(1 for word in compliment_keywords if word in text)
    
    if complaint_count > compliment_count:
        sentiment = "complaint"
    elif compliment_count > complaint_count:
        sentiment = "compliment"
    else:
        sentiment = "neutral"
    
    # Subject extraction
    subjects = []
    if any(word in text for word in ["chef", "cook", "kitchen", "food", "dish", "meal"]):
        subjects.append("chef")
    if any(word in text for word in ["delivery", "driver", "deliver", "late", "arrive"]):
        subjects.append("delivery")
    if any(word in text for word in ["food", "dish", "meal", "taste", "quality"]):
        subjects.append("food")
    if any(word in text for word in ["service", "staff", "manager", "experience"]):
        subjects.append("service")
    
    # Default to general if no subjects found
    if not subjects:
        subjects = ["general"]
    
    # Auto-label generation
    auto_labels = []
    if sentiment == "complaint":
        if "chef" in subjects:
            auto_labels.append("Complaint Chef")
        if "delivery" in subjects:
            auto_labels.append("Complaint Delivery Person")
        if "food" in subjects:
            auto_labels.append("Food Quality Issue")
        if "service" in subjects:
            auto_labels.append("Service Issue")
    elif sentiment == "compliment":
        if "chef" in subjects:
            auto_labels.append("Compliment Chef")
        if "delivery" in subjects:
            auto_labels.append("Compliment Delivery Person")
        if "food" in subjects:
            auto_labels.append("Food Quality Praise")
        if "service" in subjects:
            auto_labels.append("Excellent Service")
    else:
        auto_labels.append("General Inquiry")
    
    # Calculate confidence based on keyword matches
    confidence = min(0.95, 0.70 + (complaint_count + compliment_count) * 0.05)
    
    return AnalyzeResponse(
        sentiment=sentiment,
        subjects=subjects,
        confidence=confidence,
        auto_labels=auto_labels
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
