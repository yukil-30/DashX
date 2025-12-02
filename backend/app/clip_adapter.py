"""
CLIP Adapter for Image-Text Embeddings

This module provides integration with OpenAI's CLIP model for semantic
image understanding. CLIP (Contrastive Language-Image Pre-training) can:
- Generate semantic embeddings for images
- Match images to text descriptions
- Provide much better food similarity matching than color histograms

SETUP INSTRUCTIONS:
==================

Option 1: Local CLIP with Hugging Face (Recommended)
-----------------------------------------------------
1. Install dependencies:
   pip install torch torchvision transformers

2. Set USE_CLIP = True in image_utils.py

3. The model will download automatically on first use (~600MB)

Option 2: CLIP Service with Docker (Production)
------------------------------------------------
1. Add clip-service to docker-compose.yml:

```yaml
  clip-service:
    build: ./clip-service
    ports:
      - "8002:8002"
    environment:
      - MODEL_NAME=openai/clip-vit-base-patch32
    volumes:
      - ./clip-service/cache:/root/.cache
```

2. Create clip-service/Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install torch torchvision transformers pillow fastapi uvicorn

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

3. Create clip-service/main.py (see code below)

4. Run: docker-compose up clip-service

USAGE:
======
from app.clip_adapter import CLIPAdapter

adapter = CLIPAdapter()
embedding = adapter.encode_image(image_bytes)
similarity = adapter.compute_similarity(embedding1, embedding2)
"""

import logging
import os
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class CLIPAdapter:
    """
    Adapter for CLIP model embeddings.
    
    Supports both local CLIP and remote CLIP service.
    """
    
    def __init__(self, service_url: Optional[str] = None):
        """
        Initialize CLIP adapter.
        
        Args:
            service_url: URL of CLIP service (e.g., "http://clip-service:8002")
                        If None, uses local CLIP model
        """
        self.service_url = service_url or os.getenv("CLIP_SERVICE_URL")
        self.model = None
        self.processor = None
        
        if self.service_url:
            self._init_remote()
        else:
            self._init_local()
    
    def _init_local(self):
        """Initialize local CLIP model."""
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            model_name = "openai/clip-vit-base-patch32"
            logger.info(f"Loading CLIP model: {model_name}")
            
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model = CLIPModel.from_pretrained(model_name)
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")
                logger.info("✅ CLIP model loaded on GPU")
            else:
                logger.info("✅ CLIP model loaded on CPU")
                
        except ImportError:
            raise ImportError(
                "CLIP dependencies not installed. Run: "
                "pip install torch torchvision transformers"
            )
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
    
    def _init_remote(self):
        """Initialize connection to remote CLIP service."""
        logger.info(f"Using remote CLIP service at {self.service_url}")
        # Test connection
        try:
            import httpx
            response = httpx.get(f"{self.service_url}/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("✅ CLIP service connection verified")
            else:
                logger.warning(f"⚠️ CLIP service returned status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to CLIP service: {e}")
            raise ConnectionError(f"CLIP service unavailable at {self.service_url}")
    
    def encode_image(self, image_data: bytes) -> np.ndarray:
        """
        Encode image to CLIP embedding vector.
        
        Args:
            image_data: Raw image bytes (JPEG, PNG, etc.)
            
        Returns:
            CLIP embedding (512-dimensional vector)
        """
        if self.service_url:
            return self._encode_image_remote(image_data)
        else:
            return self._encode_image_local(image_data)
    
    def _encode_image_local(self, image_data: bytes) -> np.ndarray:
        """Encode image using local CLIP model."""
        from PIL import Image
        import io
        import torch
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Preprocess
            inputs = self.processor(images=image, return_tensors="pt")
            
            # Move to same device as model
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Get embedding
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Normalize embedding
            embedding = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Convert to numpy
            return embedding.cpu().numpy().flatten()
            
        except Exception as e:
            logger.error(f"Local CLIP encoding failed: {e}")
            raise
    
    def _encode_image_remote(self, image_data: bytes) -> np.ndarray:
        """Encode image using remote CLIP service."""
        import httpx
        
        try:
            # Send image to service
            files = {"file": ("image.jpg", image_data, "image/jpeg")}
            response = httpx.post(
                f"{self.service_url}/encode",
                files=files,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise ValueError(f"CLIP service error: {response.text}")
            
            result = response.json()
            return np.array(result["embedding"])
            
        except Exception as e:
            logger.error(f"Remote CLIP encoding failed: {e}")
            raise
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two CLIP embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity (-1 to 1, higher is more similar)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)


# Example CLIP service implementation (clip-service/main.py)
CLIP_SERVICE_CODE = '''
"""
CLIP Embedding Service

Standalone FastAPI service for CLIP image embeddings.
Run with: uvicorn main:app --host 0.0.0.0 --port 8002
"""

import io
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CLIP Embedding Service")

# Load model at startup
MODEL_NAME = "openai/clip-vit-base-patch32"
logger.info(f"Loading CLIP model: {MODEL_NAME}")
processor = CLIPProcessor.from_pretrained(MODEL_NAME)
model = CLIPModel.from_pretrained(MODEL_NAME)

if torch.cuda.is_available():
    model = model.to("cuda")
    logger.info("✅ Model loaded on GPU")
else:
    logger.info("✅ Model loaded on CPU")


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/encode")
async def encode_image(file: UploadFile = File(...)):
    """Encode image to CLIP embedding."""
    try:
        # Read image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Process
        inputs = processor(images=image, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Encode
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # Normalize
        embedding = image_features / image_features.norm(dim=-1, keepdim=True)
        
        # Convert to list for JSON
        embedding_list = embedding.cpu().numpy().flatten().tolist()
        
        return {"embedding": embedding_list}
        
    except Exception as e:
        logger.error(f"Encoding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
'''


def save_clip_service_code(output_dir: str = "./clip-service"):
    """
    Save CLIP service code to directory.
    
    Args:
        output_dir: Directory to save service files
    """
    import os
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save main.py
    with open(output_path / "main.py", "w") as f:
        f.write(CLIP_SERVICE_CODE)
    
    # Save Dockerfile
    dockerfile = """FROM python:3.11-slim

WORKDIR /app

RUN pip install torch torchvision transformers pillow fastapi uvicorn

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
"""
    with open(output_path / "Dockerfile", "w") as f:
        f.write(dockerfile)
    
    # Save requirements.txt
    requirements = """torch>=2.0.0
torchvision>=0.15.0
transformers>=4.30.0
Pillow>=10.0.0
fastapi>=0.100.0
uvicorn>=0.22.0
python-multipart>=0.0.6
"""
    with open(output_path / "requirements.txt", "w") as f:
        f.write(requirements)
    
    logger.info(f"✅ CLIP service code saved to {output_path}")
    print(f"\nTo run CLIP service:")
    print(f"  cd {output_dir}")
    print(f"  docker build -t clip-service .")
    print(f"  docker run -p 8002:8002 clip-service")
