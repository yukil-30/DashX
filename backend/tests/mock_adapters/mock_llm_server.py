"""
Mock LLM Server for Testing
Simulates local LLM responses without requiring actual model.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="Mock LLM Server")


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.7


class GenerateResponse(BaseModel):
    text: str
    model: str = "mock-llm-v1"
    tokens_used: int


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-llm"}


@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Mock LLM generation endpoint"""
    prompt = request.prompt.lower()
    
    # Simple keyword-based responses
    if "menu" in prompt or "dishes" in prompt or "food" in prompt:
        response = "We offer a variety of delicious dishes including burgers, pizzas, salads, pasta, and desserts. All our dishes are freshly prepared by our expert chefs."
    elif "order" in prompt or "delivery" in prompt:
        response = "You can place an order through our website. We offer delivery service with competitive bidding from our delivery partners. Estimated delivery time is 30-45 minutes."
    elif "vip" in prompt or "premium" in prompt:
        response = "VIP membership is automatically granted after 3 completed orders or $100 in total spending. VIP members receive 5% discount on all orders and free delivery credits."
    elif "complaint" in prompt or "problem" in prompt or "issue" in prompt:
        response = "We apologize for any inconvenience. Please file a formal complaint through the app, and our manager will review it promptly. You can also use voice reporting for faster processing."
    elif "payment" in prompt or "balance" in prompt:
        response = "You can add funds to your account balance through the deposit feature. All payments are processed securely, and you'll see the balance update immediately."
    else:
        response = f"Thank you for your question. Our team has noted your inquiry: '{request.prompt[:100]}'. A manager will provide a detailed answer shortly."
    
    return GenerateResponse(
        text=response,
        tokens_used=len(response.split())
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
