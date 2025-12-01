"""
LLM Stub Service
A simple HTTP server that returns canned responses for development.
This will be replaced with Ollama or Hugging Face later.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI(
    title="LLM Stub Service",
    description="Stub service for local LLM - returns canned responses for development",
    version="0.1.0"
)


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    response: str
    model: str = "stub-llm-v1"
    tokens_used: int


class MenuRecommendationRequest(BaseModel):
    preferences: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = []
    budget: Optional[str] = None


class MenuRecommendationResponse(BaseModel):
    recommendations: List[str]
    reasoning: str


# Canned responses for menu recommendations
MENU_RECOMMENDATIONS = [
    {
        "recommendations": [
            "Grilled Salmon with Lemon Butter",
            "Caesar Salad",
            "Chocolate Lava Cake"
        ],
        "reasoning": "Based on your preferences, I recommend starting with our fresh Caesar Salad, followed by our signature Grilled Salmon. For dessert, our Chocolate Lava Cake is a must-try!"
    },
    {
        "recommendations": [
            "Mushroom Risotto",
            "Tomato Bruschetta",
            "Tiramisu"
        ],
        "reasoning": "For a delightful Italian experience, try our creamy Mushroom Risotto. Start with Tomato Bruschetta and end with classic Tiramisu."
    },
    {
        "recommendations": [
            "Grilled Chicken Breast",
            "Garden Salad",
            "Fresh Fruit Plate"
        ],
        "reasoning": "For a healthy option, our Grilled Chicken Breast with Garden Salad is perfect. Finish with our refreshing Fresh Fruit Plate."
    }
]

# Canned chat responses
CHAT_RESPONSES = [
    "I'd be happy to help you with your order! Our specials today include fresh seafood and seasonal vegetables.",
    "Our chef recommends the pasta of the day - it's made with locally sourced ingredients.",
    "For dietary restrictions, we can accommodate vegetarian, vegan, gluten-free, and nut-free options.",
    "Our most popular dishes are the Grilled Salmon and the Mushroom Risotto.",
    "We have a great selection of wines that pair perfectly with our menu items.",
]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model": "stub-llm-v1",
        "message": "LLM Stub service is running. Replace with Ollama/HF for production."
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - returns canned responses.
    In production, this will forward to Ollama or Hugging Face.
    """
    # Get the last user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message provided")
    
    # Return a random canned response
    response = random.choice(CHAT_RESPONSES)
    
    return ChatResponse(
        response=response,
        tokens_used=len(response.split())
    )


@app.post("/recommend", response_model=MenuRecommendationResponse)
async def recommend_menu(request: MenuRecommendationRequest):
    """
    Menu recommendation endpoint.
    Returns canned recommendations based on preferences.
    """
    # Select a recommendation based on dietary restrictions
    if request.dietary_restrictions:
        if "vegetarian" in request.dietary_restrictions or "vegan" in request.dietary_restrictions:
            recommendation = MENU_RECOMMENDATIONS[1]  # Vegetarian-friendly option
        else:
            recommendation = MENU_RECOMMENDATIONS[2]  # Healthy option
    else:
        recommendation = random.choice(MENU_RECOMMENDATIONS)
    
    return MenuRecommendationResponse(
        recommendations=recommendation["recommendations"],
        reasoning=recommendation["reasoning"]
    )


@app.get("/models")
async def list_models():
    """List available models (stub)"""
    return {
        "models": [
            {
                "name": "stub-llm-v1",
                "description": "Stub LLM for development",
                "status": "active"
            }
        ],
        "note": "Replace with Ollama models in production"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Stub",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/chat": "Chat completion (POST)",
            "/recommend": "Menu recommendations (POST)",
            "/models": "List available models"
        }
    }
