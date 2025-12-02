"""
Local AI-enabled Restaurant Backend
FastAPI Application Entry Point
"""

import os
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

from app.auth import require_manager
from app.models import Account

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "true").lower() == "true" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Static files directory - use local path if not in Docker
if os.path.exists("/app"):
    STATIC_DIR = Path("/app/static")
else:
    STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_IMAGES_DIR = STATIC_DIR / "images"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("🚀 Starting Local AI-enabled Restaurant API...")
    logger.info(f"   Debug mode: {os.getenv('DEBUG', 'true')}")
    logger.info(f"   LLM URL: {os.getenv('LLM_STUB_URL', 'http://llm-stub:8001')}")
    
    # Ensure static directories exist
    STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"   Static images dir: {STATIC_IMAGES_DIR}")
    
    # Start background tasks
    background_task = None
    if os.getenv("ENABLE_BACKGROUND_TASKS", "true").lower() == "true":
        from app.background_tasks import periodic_performance_evaluation
        background_task = asyncio.create_task(periodic_performance_evaluation())
        logger.info("   Background performance evaluation task started")
    
    yield
    
    # Shutdown
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    logger.info("👋 Shutting down API...")


app = FastAPI(
    title="Local AI-enabled Restaurant API",
    description="Backend API for the AI-powered restaurant management system",
    version="0.1.0",
    lifespan=lifespan
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if os.getenv("DEBUG", "true").lower() == "true" else "An unexpected error occurred",
            "status_code": 500,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of the API and its dependencies.
    """
    db_status = "not_checked"
    llm_status = "not_checked"
    
    # Check database connection
    try:
        from app.database import check_connection
        if check_connection():
            db_status = "connected"
            logger.debug("Database health check: connected")
        else:
            db_status = "disconnected"
            logger.warning("Database health check: disconnected")
    except ImportError:
        db_status = "not_configured"
        logger.debug("Database module not configured")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Database health check error: {e}")
    
    # Check LLM stub connection
    llm_url = os.getenv("LLM_STUB_URL", "http://llm-stub:8001")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{llm_url}/health")
            if response.status_code == 200:
                llm_status = "connected"
                logger.debug("LLM stub health check: connected")
            else:
                llm_status = f"unhealthy: {response.status_code}"
                logger.warning(f"LLM stub returned status {response.status_code}")
    except httpx.ConnectError:
        llm_status = "connection_failed"
        logger.warning(f"LLM stub connection failed at {llm_url}")
    except httpx.TimeoutException:
        llm_status = "timeout"
        logger.warning(f"LLM stub request timed out at {llm_url}")
    except Exception as e:
        llm_status = f"error: {str(e)}"
        logger.error(f"LLM stub health check error: {e}")
    
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
        "health": "/health",
        "version": "0.1.0"
    }


# Import and register routers
from app.routers import auth, account, dishes, home, orders, bids, reputation, chat
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(dishes.router)
app.include_router(home.router)
app.include_router(orders.router)
app.include_router(bids.router)
app.include_router(reputation.router)
app.include_router(chat.router)


@app.post("/admin/evaluate-performance", tags=["Admin"])
async def trigger_performance_evaluation(
    current_user: Account = Depends(require_manager)
):
    """
    Manually trigger performance evaluation for all chefs and delivery personnel.
    Manager only.
    """
    from app.background_tasks import run_immediate_evaluation
    
    results = run_immediate_evaluation()
    
    return {
        "message": "Performance evaluation completed",
        "results": results
    }

# Mount static files for image serving
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory {STATIC_DIR} does not exist, creating it...")
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Future routers
# from app.routers import orders, ai
# app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
# app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
