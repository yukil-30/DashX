"""
Tests for the Local LLM Adapter

These tests verify the LocalLLMServiceAdapter class works correctly
with the local-llm Docker service.

To run these tests:
    1. Start the local-llm service: docker compose --profile local-llm up -d local-llm
    2. Run: pytest tests/test_local_llm_adapter.py -v

For unit tests without the service, use the mocked tests.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the adapter classes
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from llm_adapter import (
    DockerLocalLLMAdapter,
    LLMResponse,
    LLMCache,
    get_llm_adapter
)


class TestDockerLocalLLMAdapterUnit:
    """Unit tests for DockerLocalLLMAdapter (mocked, no service required)"""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance"""
        return DockerLocalLLMAdapter(
            base_url="http://test-llm:8080",
            cache=LLMCache(ttl_seconds=60)
        )
    
    def test_adapter_name(self, adapter):
        """Test adapter name property"""
        assert adapter.name == "docker-local-llm"
    
    def test_adapter_default_url(self):
        """Test default URL is used when not specified"""
        with patch.dict(os.environ, {"LOCAL_LLM_URL": "http://custom:9000"}):
            adapter = DockerLocalLLMAdapter()
            assert adapter.base_url == "http://custom:9000"
    
    @pytest.mark.asyncio
    async def test_generate_success(self, adapter):
        """Test successful generation"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Test response",
            "tokens_used": 5,
            "model": "local-llm",
            "latency_ms": 100.0
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await adapter.generate("Test question")
            
            assert result.answer == "Test response"
            assert result.model == "local-llm"
            assert result.confidence == 0.6
            assert result.error is None
    
    @pytest.mark.asyncio
    async def test_generate_with_context(self, adapter):
        """Test generation with context"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Contextual response",
            "tokens_used": 10,
            "model": "local-llm"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await adapter.generate(
                "What dishes do you have?",
                context="Restaurant menu context"
            )
            
            # Verify the prompt includes context
            call_args = mock_instance.post.call_args
            json_data = call_args.kwargs.get('json', call_args[1].get('json', {}))
            assert "<|im_start|>system" in json_data.get("prompt", "")
            assert "Restaurant menu context" in json_data.get("prompt", "")
            assert result.answer == "Contextual response"
    
    @pytest.mark.asyncio
    async def test_generate_cache_hit(self, adapter):
        """Test that cached responses are returned"""
        # Pre-populate cache
        cached_response = LLMResponse(
            answer="Cached answer",
            model="local-llm",
            confidence=0.7,
            cached=True
        )
        adapter.cache.set("Test question", cached_response)
        
        result = await adapter.generate("Test question")
        
        assert result.answer == "Cached answer"
        assert result.cached is True
    
    @pytest.mark.asyncio
    async def test_generate_connection_error(self, adapter):
        """Test error handling on connection errors"""
        with patch('httpx.AsyncClient') as mock_client:
            import httpx
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            result = await adapter.generate("Test question")
            
            assert result.answer == ""
            assert result.error is not None
            assert "Cannot connect" in result.error
    
    def test_health_check_success(self, adapter):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "model_loaded": True,
            "stub_mode": False
        }
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = adapter.health_check()
            
            assert result["status"] == "ok"
            assert result["adapter"] == "docker-local-llm"
            assert result["model_loaded"] is True
    
    def test_health_check_failure(self, adapter):
        """Test health check when service is unavailable"""
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection refused")
            
            result = adapter.health_check()
            
            assert result["status"] == "error"
            assert "error" in result


class TestGetLLMAdapter:
    """Test the get_llm_adapter factory function"""
    
    def test_get_stub_adapter_default(self):
        """Test that stub adapter is returned by default"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_ADAPTER", None)
            os.environ.pop("ENABLE_LOCAL_LLM", None)
            adapter = get_llm_adapter()
            assert adapter.name == "stub"
    
    def test_get_local_adapter_explicit(self):
        """Test explicit local adapter selection"""
        adapter = get_llm_adapter("local")
        assert adapter.name == "docker-local-llm"
    
    def test_get_local_adapter_via_env(self):
        """Test local adapter via LLM_ADAPTER env var"""
        with patch.dict(os.environ, {"LLM_ADAPTER": "local"}):
            adapter = get_llm_adapter()
            assert adapter.name == "docker-local-llm"
    
    def test_get_local_adapter_via_enable_flag(self):
        """Test local adapter via ENABLE_LOCAL_LLM flag"""
        with patch.dict(os.environ, {"ENABLE_LOCAL_LLM": "true"}):
            adapter = get_llm_adapter()
            assert adapter.name == "docker-local-llm"
    
    def test_get_ollama_adapter(self):
        """Test Ollama adapter selection"""
        adapter = get_llm_adapter("ollama")
        assert "ollama" in adapter.name
    
    def test_get_huggingface_adapter(self):
        """Test HuggingFace adapter selection"""
        adapter = get_llm_adapter("huggingface")
        assert "huggingface" in adapter.name


@pytest.mark.integration
class TestDockerLocalLLMAdapterIntegration:
    """
    Integration tests that require the local-llm service to be running.
    
    Run with: pytest tests/test_local_llm_adapter.py -v -m integration
    
    Prerequisites:
        docker compose --profile local-llm up -d local-llm
    """
    
    @pytest.fixture
    def adapter(self):
        """Create adapter pointing to real service"""
        return DockerLocalLLMAdapter(
            base_url=os.getenv("LOCAL_LLM_URL", "http://localhost:8080")
        )
    
    @pytest.fixture(autouse=True)
    def check_service(self):
        """Skip if service is not running"""
        import httpx
        try:
            response = httpx.get("http://localhost:8080/health", timeout=2.0)
            if response.status_code != 200:
                pytest.skip("Local LLM service not healthy")
        except Exception:
            pytest.skip("Local LLM service not running")
    
    @pytest.mark.asyncio
    async def test_real_generate(self, adapter):
        """Test real generation against service"""
        result = await adapter.generate("What is 2 + 2?")
        
        assert result.answer != ""
        assert result.error is None
        assert result.latency_ms > 0
    
    def test_real_health_check(self, adapter):
        """Test real health check against service"""
        result = adapter.health_check()
        
        assert result["status"] == "ok"
        assert result["adapter"] == "docker-local-llm"
