"""
Local AI-enabled Restaurant Backend
FastAPI Application Entry Point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI(
    title="Local AI-enabled Restaurant API",
    description="Backend API for the AI-powered restaurant management system",
    version="0.1.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str = "0.1.0"
    database: str = "not_checked"
    llm_stub: str = "not_checked"


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    detail: str
    status_code: int


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of the API and its dependencies.
    """
    db_status = "not_checked"
    llm_status = "not_checked"
    
    # Check database connection (will be implemented with actual DB)
    try:
        from app.database import check_connection
        if check_connection():
            db_status = "connected"
        else:
            db_status = "disconnected"
    except ImportError:
        db_status = "not_configured"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check LLM stub connection
    llm_url = os.getenv("LLM_STUB_URL", "http://llm-stub:8001")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{llm_url}/health")
            if response.status_code == 200:
                llm_status = "connected"
            else:
                llm_status = f"unhealthy: {response.status_code}"
    except httpx.ConnectError:
        llm_status = "connection_failed"
    except httpx.TimeoutException:
        llm_status = "timeout"
    except Exception as e:
        llm_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="ok",
        database=db_status,
        llm_stub=llm_status
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Local AI-enabled Restaurant API",
        "docs": "/docs",
        "health": "/health"
    }


# Import routers when they exist
# from app.routers import menu, orders, ai
# app.include_router(menu.router, prefix="/api/menu", tags=["Menu"])
# app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
# app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
