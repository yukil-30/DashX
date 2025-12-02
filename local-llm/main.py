"""
Local LLM Server

A lightweight server that wraps llama-cpp-python to provide a simple HTTP API
compatible with the DashX LLM adapter interface.

API:
  POST /v1/generate  {"prompt": "...", "max_tokens": 256} -> {"text": "..."}
  GET  /health       -> {"status": "ok"}

This server is designed to run in Docker with a GGUF model file mounted at
/models/model.gguf or specified via MODEL_PATH environment variable.

If no model is available, it falls back to a stub mode that returns canned responses.
"""

import os
import logging
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("local-llm")

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/models/model.gguf")
N_CTX = int(os.getenv("N_CTX", "2048"))  # Context window
N_THREADS = int(os.getenv("N_THREADS", "4"))  # CPU threads
N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "0"))  # GPU layers (0 = CPU only)
STUB_MODE = os.getenv("STUB_MODE", "false").lower() == "true"
# Chat format for TinyLlama and similar models
# Options: "none", "tinyllama", "chatml", "alpaca"
CHAT_FORMAT = os.getenv("CHAT_FORMAT", "tinyllama")

# Global model instance
llm = None
model_loaded = False
stub_mode_active = False


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to generate text from")
    max_tokens: int = Field(default=256, ge=1, le=2048, description="Maximum tokens to generate")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    stop: Optional[list[str]] = Field(default=None, description="Stop sequences")


class GenerateResponse(BaseModel):
    text: str = Field(..., description="Generated text")
    tokens_used: int = Field(default=0, description="Number of tokens generated")
    model: str = Field(default="local-llm", description="Model identifier")
    latency_ms: float = Field(default=0.0, description="Generation latency in milliseconds")


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool = False
    stub_mode: bool = False
    model_path: Optional[str] = None
    message: Optional[str] = None


# Canned responses for stub mode
STUB_RESPONSES = [
    "I'm a local AI assistant. I can help you with questions about the restaurant.",
    "That's a great question! Our restaurant offers a variety of delicious dishes.",
    "I'd be happy to help you explore our menu options.",
    "Thank you for your inquiry. Our team is here to assist you.",
    "Let me help you with that. What would you like to know?",
]
stub_response_idx = 0


def format_prompt_for_chat(prompt: str) -> str:
    """
    Format prompt for chat models based on CHAT_FORMAT setting.
    
    Supports:
    - none: Pass prompt as-is
    - tinyllama: TinyLlama chat format (<|user|>...<|assistant|>)
    - chatml: ChatML format (<|im_start|>...<|im_end|>)
    - alpaca: Alpaca instruction format
    """
    if CHAT_FORMAT == "none":
        return prompt
    
    # Check if prompt is already formatted (contains chat tokens)
    chat_tokens = ["<|user|>", "<|assistant|>", "<|im_start|>", "### Instruction"]
    if any(token in prompt for token in chat_tokens):
        return prompt
    
    if CHAT_FORMAT == "tinyllama":
        return f"<|user|>\n{prompt}\n<|assistant|>\n"
    
    elif CHAT_FORMAT == "chatml":
        return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    
    elif CHAT_FORMAT == "alpaca":
        return f"### Instruction:\n{prompt}\n\n### Response:\n"
    
    else:
        # Default to tinyllama format
        return f"<|user|>\n{prompt}\n<|assistant|>\n"


def load_model():
    """Attempt to load the LLM model"""
    global llm, model_loaded, stub_mode_active
    
    if STUB_MODE:
        logger.info("Running in STUB_MODE - no model will be loaded")
        stub_mode_active = True
        return
    
    if not os.path.exists(MODEL_PATH):
        logger.warning(f"Model not found at {MODEL_PATH}")
        logger.info("To download a model, run: ./scripts/download_model.sh")
        logger.info("Falling back to stub mode")
        stub_mode_active = True
        return
    
    try:
        from llama_cpp import Llama
        
        logger.info(f"Loading model from {MODEL_PATH}...")
        logger.info(f"  Context size: {N_CTX}")
        logger.info(f"  Threads: {N_THREADS}")
        logger.info(f"  GPU layers: {N_GPU_LAYERS}")
        
        start_time = time.time()
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False
        )
        load_time = time.time() - start_time
        
        logger.info(f"✓ Model loaded successfully in {load_time:.1f}s")
        model_loaded = True
        
    except ImportError:
        logger.error("llama-cpp-python not installed")
        logger.info("Falling back to stub mode")
        stub_mode_active = True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.info("Falling back to stub mode")
        stub_mode_active = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup"""
    load_model()
    yield
    # Cleanup
    global llm
    llm = None


app = FastAPI(
    title="Local LLM Server",
    description="Lightweight local LLM server for DashX",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if model_loaded:
        return HealthResponse(
            status="ok",
            model_loaded=True,
            stub_mode=False,
            model_path=MODEL_PATH,
            message="Model loaded and ready"
        )
    elif stub_mode_active:
        return HealthResponse(
            status="ok",
            model_loaded=False,
            stub_mode=True,
            model_path=None,
            message="Running in stub mode - no model loaded"
        )
    else:
        return HealthResponse(
            status="error",
            model_loaded=False,
            stub_mode=False,
            message="Model not loaded and stub mode not active"
        )


@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate text from a prompt.
    
    If a model is loaded, uses llama.cpp for inference.
    Otherwise, returns canned responses (stub mode).
    """
    global stub_response_idx
    
    start_time = time.time()
    
    if model_loaded and llm is not None:
        try:
            # Format prompt for chat models
            formatted_prompt = format_prompt_for_chat(request.prompt)
            
            # Set default stop sequences for chat formats
            stop_sequences = request.stop
            if stop_sequences is None and CHAT_FORMAT != "none":
                if CHAT_FORMAT == "tinyllama":
                    stop_sequences = ["<|user|>", "</s>"]
                elif CHAT_FORMAT == "chatml":
                    stop_sequences = ["<|im_end|>", "<|im_start|>"]
                elif CHAT_FORMAT == "alpaca":
                    stop_sequences = ["### Instruction", "###"]
            
            output = llm(
                formatted_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop=stop_sequences,
                echo=False
            )
            
            text = output["choices"][0]["text"].strip()
            tokens = output.get("usage", {}).get("completion_tokens", 0)
            latency = (time.time() - start_time) * 1000
            
            return GenerateResponse(
                text=text,
                tokens_used=tokens,
                model="local-llm",
                latency_ms=latency
            )
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    
    elif stub_mode_active:
        # Return canned response
        response_text = STUB_RESPONSES[stub_response_idx]
        stub_response_idx = (stub_response_idx + 1) % len(STUB_RESPONSES)
        latency = (time.time() - start_time) * 1000
        
        return GenerateResponse(
            text=response_text,
            tokens_used=len(response_text.split()),
            model="stub-local-llm",
            latency_ms=latency
        )
    
    else:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded and stub mode not active"
        )


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Local LLM Server",
        "version": "1.0.0",
        "model_loaded": model_loaded,
        "stub_mode": stub_mode_active,
        "endpoints": {
            "/health": "GET - Health check",
            "/v1/generate": "POST - Generate text from prompt"
        }
    }


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI API compatible)"""
    models = []
    
    if model_loaded:
        models.append({
            "id": "local-llm",
            "object": "model",
            "owned_by": "local",
            "permission": []
        })
    
    if stub_mode_active:
        models.append({
            "id": "stub-local-llm",
            "object": "model",
            "owned_by": "local",
            "permission": []
        })
    
    return {"object": "list", "data": models}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
