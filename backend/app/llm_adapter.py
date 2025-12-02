"""
Local LLM Adapter Interface and Implementations

Provides a pluggable adapter system for different LLM backends:
- StubAdapter: Returns canned responses (development/testing)
- LocalLLMAdapter: Connects to the local-llm Docker service (llama.cpp based)
- OllamaAdapter: Connects to local Ollama instance
- HuggingFaceAdapter: Uses HuggingFace Transformers locally

Configuration:
--------------
Set environment variables to configure:
  LLM_ADAPTER: 'stub', 'local', 'ollama', or 'huggingface' (default: 'stub')
  LLM_STUB_URL: URL for stub service (default: http://llm-stub:8001)
  LOCAL_LLM_URL: URL for local LLM service (default: http://local-llm:8080)
  ENABLE_LOCAL_LLM: Set to 'true' to auto-switch to local adapter
  OLLAMA_URL: URL for Ollama API (default: http://localhost:11434)
  OLLAMA_MODEL: Model name for Ollama (default: llama2)
  HF_MODEL: HuggingFace model name (default: gpt2)
  LLM_CACHE_TTL: Cache TTL in seconds (default: 3600)
"""

import os
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM adapter"""
    answer: str
    model: str
    confidence: float = 0.5  # Default confidence for LLM responses
    tokens_used: int = 0
    cached: bool = False
    error: Optional[str] = None
    latency_ms: float = 0.0  # Track response time


@dataclass
class CacheEntry:
    """Cache entry for LLM responses"""
    response: LLMResponse
    created_at: datetime
    hits: int = 0


class LLMCache:
    """
    Simple in-memory cache for LLM responses.
    Avoids repeated LLM calls for identical questions.
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 1000):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
    
    def _make_key(self, question: str, context: Optional[str] = None) -> str:
        """Generate cache key from question and context"""
        content = f"{question.lower().strip()}:{context or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def get(self, question: str, context: Optional[str] = None) -> Optional[LLMResponse]:
        """Get cached response if exists and not expired"""
        key = self._make_key(question, context)
        entry = self._cache.get(key)
        
        if entry is None:
            return None
        
        # Check if expired
        if datetime.now() - entry.created_at > self.ttl:
            del self._cache[key]
            return None
        
        entry.hits += 1
        response = entry.response
        response.cached = True
        return response
    
    def set(self, question: str, response: LLMResponse, context: Optional[str] = None):
        """Cache a response"""
        # Evict oldest entries if at capacity
        if len(self._cache) >= self.max_entries:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
        
        key = self._make_key(question, context)
        self._cache[key] = CacheEntry(
            response=response,
            created_at=datetime.now()
        )
    
    def clear(self):
        """Clear all cached entries"""
        self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(e.hits for e in self._cache.values())
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "total_hits": total_hits,
            "ttl_seconds": self.ttl.total_seconds()
        }


class LocalLLMAdapter(ABC):
    """Abstract base class for LLM adapters"""
    
    def __init__(self, cache: Optional[LLMCache] = None):
        self.cache = cache
    
    @abstractmethod
    async def generate(self, question: str, context: Optional[str] = None) -> LLMResponse:
        """
        Generate a response to a question.
        
        Args:
            question: The user's question
            context: Optional context to help answer the question
            
        Returns:
            LLMResponse with the generated answer
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check if the LLM backend is available"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return adapter name"""
        pass
    
    def _check_cache(self, question: str, context: Optional[str] = None) -> Optional[LLMResponse]:
        """Check cache for existing response"""
        if self.cache:
            return self.cache.get(question, context)
        return None
    
    def _cache_response(self, question: str, response: LLMResponse, context: Optional[str] = None):
        """Cache a response"""
        if self.cache:
            self.cache.set(question, response, context)


class StubAdapter(LocalLLMAdapter):
    """
    Stub adapter that returns canned responses.
    Used for development and testing when no LLM is available.
    """
    
    CANNED_RESPONSES = [
        "I'd be happy to help you with that! Based on our restaurant's offerings, I recommend checking out our daily specials.",
        "Great question! Our menu features a variety of options to suit different tastes and dietary needs.",
        "Thank you for your inquiry. For the most accurate information, please contact our staff directly.",
        "I can help with that. Our restaurant prides itself on fresh, locally-sourced ingredients.",
        "That's a popular request! Let me suggest some of our top-rated dishes for you to consider.",
    ]
    
    def __init__(self, base_url: Optional[str] = None, cache: Optional[LLMCache] = None):
        super().__init__(cache)
        self.base_url = base_url or os.getenv("LLM_STUB_URL", "http://llm-stub:8001")
        self._response_index = 0
    
    @property
    def name(self) -> str:
        return "stub"
    
    async def generate(self, question: str, context: Optional[str] = None) -> LLMResponse:
        """Generate response - tries stub service first, falls back to canned responses"""
        import time
        start_time = time.time()
        
        # Check cache first
        cached = self._check_cache(question, context)
        if cached:
            logger.debug(f"Cache hit for question: {question[:50]}...")
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json={
                        "messages": [
                            {"role": "system", "content": context or "You are a helpful restaurant assistant."},
                            {"role": "user", "content": question}
                        ]
                    }
                )
                latency = (time.time() - start_time) * 1000
                if response.status_code == 200:
                    data = response.json()
                    result = LLMResponse(
                        answer=data.get("response", self._get_canned_response()),
                        model=data.get("model", "stub-llm-v1"),
                        confidence=0.5,
                        tokens_used=data.get("tokens_used", 0),
                        latency_ms=latency
                    )
                    self._cache_response(question, result, context)
                    return result
        except Exception as e:
            logger.warning(f"Stub service unavailable: {e}, using canned response")
        
        # Fall back to canned response
        latency = (time.time() - start_time) * 1000
        result = LLMResponse(
            answer=self._get_canned_response(),
            model="stub-local",
            confidence=0.3,
            tokens_used=0,
            latency_ms=latency
        )
        self._cache_response(question, result, context)
        return result
    
    def _get_canned_response(self) -> str:
        """Get next canned response (round-robin)"""
        response = self.CANNED_RESPONSES[self._response_index]
        self._response_index = (self._response_index + 1) % len(self.CANNED_RESPONSES)
        return response
    
    def health_check(self) -> Dict[str, Any]:
        """Check stub service health"""
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return {"status": "ok", "adapter": "stub", "service": "connected"}
        except Exception as e:
            logger.debug(f"Stub service health check failed: {e}")
        
        return {"status": "ok", "adapter": "stub", "service": "fallback_mode"}


class OllamaAdapter(LocalLLMAdapter):
    """
    Adapter for Ollama local LLM.
    
    Setup:
    ------
    1. Install Ollama: https://ollama.ai
    2. Pull a model: ollama pull llama2
    3. Start Ollama: ollama serve
    4. Set OLLAMA_URL and OLLAMA_MODEL environment variables
    """
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        model: Optional[str] = None,
        cache: Optional[LLMCache] = None
    ):
        super().__init__(cache)
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama2")
    
    @property
    def name(self) -> str:
        return f"ollama:{self.model}"
    
    async def generate(self, question: str, context: Optional[str] = None) -> LLMResponse:
        """Generate response using Ollama"""
        # Check cache first
        cached = self._check_cache(question, context)
        if cached:
            logger.debug(f"Cache hit for question: {question[:50]}...")
            return cached
        
        prompt = question
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = LLMResponse(
                        answer=data.get("response", ""),
                        model=self.model,
                        confidence=0.6,
                        tokens_used=data.get("eval_count", 0)
                    )
                    self._cache_response(question, result, context)
                    return result
                else:
                    logger.error(f"Ollama error: {response.status_code} - {response.text}")
                    return LLMResponse(
                        answer="",
                        model=self.model,
                        confidence=0.0,
                        error=f"Ollama returned status {response.status_code}"
                    )
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            return LLMResponse(
                answer="",
                model=self.model,
                confidence=0.0,
                error=f"Cannot connect to Ollama: {e}"
            )
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return LLMResponse(
                answer="",
                model=self.model,
                confidence=0.0,
                error=str(e)
            )
    
    def health_check(self) -> Dict[str, Any]:
        """Check Ollama health"""
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {
                        "status": "ok",
                        "adapter": "ollama",
                        "url": self.base_url,
                        "model": self.model,
                        "available_models": models
                    }
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
        
        return {
            "status": "error",
            "adapter": "ollama",
            "url": self.base_url,
            "error": "Cannot connect to Ollama"
        }


class HuggingFaceAdapter(LocalLLMAdapter):
    """
    Adapter for local HuggingFace Transformers.
    
    Setup:
    ------
    1. Install transformers: pip install transformers torch
    2. Set HF_MODEL environment variable (default: gpt2)
    
    Note: This loads the model locally and requires sufficient RAM/GPU.
    For larger models, consider using Ollama instead.
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = None,
        cache: Optional[LLMCache] = None
    ):
        super().__init__(cache)
        self.model_name = model_name or os.getenv("HF_MODEL", "gpt2")
        self._pipeline = None
        self._load_error = None
    
    @property
    def name(self) -> str:
        return f"huggingface:{self.model_name}"
    
    def _load_pipeline(self):
        """Lazy load the HuggingFace pipeline"""
        if self._pipeline is not None or self._load_error is not None:
            return
        
        try:
            from transformers import pipeline
            logger.info(f"Loading HuggingFace model: {self.model_name}")
            self._pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                max_new_tokens=150,
                do_sample=True,
                temperature=0.7
            )
            logger.info(f"HuggingFace model loaded: {self.model_name}")
        except ImportError:
            self._load_error = "transformers package not installed"
            logger.error("HuggingFace adapter requires 'transformers' package")
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"Failed to load HuggingFace model: {e}")
    
    async def generate(self, question: str, context: Optional[str] = None) -> LLMResponse:
        """Generate response using HuggingFace model"""
        # Check cache first
        cached = self._check_cache(question, context)
        if cached:
            logger.debug(f"Cache hit for question: {question[:50]}...")
            return cached
        
        self._load_pipeline()
        
        if self._load_error:
            return LLMResponse(
                answer="",
                model=self.model_name,
                confidence=0.0,
                error=self._load_error
            )
        
        prompt = question
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
        
        try:
            # Run in thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None,
                lambda: self._pipeline(prompt, max_new_tokens=150, num_return_sequences=1)
            )
            
            generated_text = outputs[0]["generated_text"]
            # Extract answer after the prompt
            answer = generated_text[len(prompt):].strip()
            
            result = LLMResponse(
                answer=answer,
                model=self.model_name,
                confidence=0.5,
                tokens_used=len(answer.split())
            )
            self._cache_response(question, result, context)
            return result
            
        except Exception as e:
            logger.error(f"HuggingFace generate error: {e}")
            return LLMResponse(
                answer="",
                model=self.model_name,
                confidence=0.0,
                error=str(e)
            )
    
    def health_check(self) -> Dict[str, Any]:
        """Check HuggingFace adapter health"""
        self._load_pipeline()
        
        if self._load_error:
            return {
                "status": "error",
                "adapter": "huggingface",
                "model": self.model_name,
                "error": self._load_error
            }
        
        return {
            "status": "ok",
            "adapter": "huggingface",
            "model": self.model_name,
            "loaded": self._pipeline is not None
        }


# Global cache instance
_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Get or create global LLM cache"""
    global _llm_cache
    if _llm_cache is None:
        ttl = int(os.getenv("LLM_CACHE_TTL", "3600"))
        _llm_cache = LLMCache(ttl_seconds=ttl)
    return _llm_cache


def get_llm_adapter(adapter_type: Optional[str] = None) -> LocalLLMAdapter:
    """
    Factory function to get the configured LLM adapter.
    
    Args:
        adapter_type: Override adapter type ('stub', 'ollama', 'huggingface')
                     If None, uses LLM_ADAPTER environment variable.
    
    Returns:
        Configured LLM adapter instance with caching enabled
    """
    cache = get_llm_cache()
    adapter_type = adapter_type or os.getenv("LLM_ADAPTER", "stub")
    
    if adapter_type == "ollama":
        return OllamaAdapter(cache=cache)
    elif adapter_type == "huggingface":
        return HuggingFaceAdapter(cache=cache)
    else:
        return StubAdapter(cache=cache)
