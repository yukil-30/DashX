"""
Image Feature Extraction and Matching Utilities

This module provides:
1. STUB IMPLEMENTATION: Simple color histogram matching for demo purposes
2. CLIP INTEGRATION: Ready-to-use interface for CLIP embeddings (when available)

STUB APPROACH:
- Extract RGB color histograms from images
- Compare histograms using Chi-squared distance
- Simple and works without external models

CLIP UPGRADE PATH:
- Uses CLIP (Contrastive Language-Image Pre-training) for semantic similarity
- Much better accuracy for food matching
- See clip_adapter.py for integration details
"""

import logging
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Configuration
USE_CLIP = False  # Set to True when CLIP is available
USE_HUGGINGFACE = True  # Use Hugging Face vision model (default)
HISTOGRAM_BINS = 32  # Number of bins per color channel for histogram
HF_MODEL_NAME = "nateraw/food"  # Food-specific vision model
class ImageFeatureExtractor:
    """Extract features from food images for similarity matching."""
    
    def __init__(self, use_clip: bool = False, use_huggingface: bool = USE_HUGGINGFACE):
        """
        Initialize feature extractor.
        
        Args:
            use_clip: If True, use CLIP embeddings
            use_huggingface: If True, use Hugging Face vision model (default)
        """
        self.use_clip = use_clip
        self.use_huggingface = use_huggingface and not use_clip  # HF unless CLIP enabled
        self.clip_model = None
        self.hf_model = None
        self.hf_processor = None
        
        if use_clip:
            try:
                from app.clip_adapter import CLIPAdapter
                self.clip_model = CLIPAdapter()
                logger.info("✅ CLIP model loaded successfully")
            except ImportError:
                logger.warning("⚠️ CLIP adapter not found, falling back")
                self.use_clip = False
                self.use_huggingface = USE_HUGGINGFACE
            except Exception as e:
                logger.error(f"❌ Failed to load CLIP model: {e}")
                self.use_clip = False
                self.use_huggingface = USE_HUGGINGFACE
        
        if self.use_huggingface and not self.use_clip:
            try:
                from transformers import AutoImageProcessor, AutoModel
                import torch
                
                logger.info(f"Loading Hugging Face model: {HF_MODEL_NAME}")
                self.hf_processor = AutoImageProcessor.from_pretrained(HF_MODEL_NAME)
                self.hf_model = AutoModel.from_pretrained(HF_MODEL_NAME)
                self.hf_model.eval()
                
                # Move to GPU if available
                if torch.cuda.is_available():
                    self.hf_model = self.hf_model.to("cuda")
                    logger.info("✅ Hugging Face model loaded on GPU")
                else:
                    logger.info("✅ Hugging Face model loaded on CPU")
                    
            except ImportError:
                logger.warning("⚠️ Transformers not installed, falling back to histogram matching")
                self.use_huggingface = False
            except Exception as e:
                logger.error(f"❌ Failed to load Hugging Face model: {e}")
                self.use_huggingface = False
    
    def extract_features(self, image_data: bytes) -> np.ndarray:
        """
        Extract feature vector from image data.
        
        Args:
            image_data: Raw image bytes (JPEG, PNG, etc.)
            
        Returns:
            Feature vector as numpy array
        """
        if self.use_clip and self.clip_model:
            return self._extract_clip_features(image_data)
        elif self.use_huggingface and self.hf_model:
            return self._extract_huggingface_features(image_data)
        else:
            return self._extract_histogram_features(image_data)
    
    def extract_features_from_path(self, image_path: str) -> np.ndarray:
        """
        Extract features from image file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Feature vector as numpy array
        """
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return self.extract_features(image_data)
        except Exception as e:
            logger.error(f"Failed to extract features from {image_path}: {e}")
            # Return zero vector on error
            if self.use_clip:
                return np.zeros(512)  # CLIP embedding size
            else:
                return np.zeros(HISTOGRAM_BINS * 3)  # RGB histogram
    
    def _extract_histogram_features(self, image_data: bytes) -> np.ndarray:
        """
        Extract color histogram features (STUB implementation).
        
        This is a simple baseline that:
        1. Converts image to RGB
        2. Computes histogram for each channel
        3. Normalizes and concatenates
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Normalized histogram feature vector (96 dimensions with HISTOGRAM_BINS=32)
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract RGB channels
            r, g, b = image.split()
            
            # Compute histograms
            r_hist, _ = np.histogram(np.array(r).flatten(), bins=HISTOGRAM_BINS, range=(0, 256))
            g_hist, _ = np.histogram(np.array(g).flatten(), bins=HISTOGRAM_BINS, range=(0, 256))
            b_hist, _ = np.histogram(np.array(b).flatten(), bins=HISTOGRAM_BINS, range=(0, 256))
            
            # Concatenate and normalize
            hist = np.concatenate([r_hist, g_hist, b_hist])
            hist = hist.astype(float)
            hist = hist / (hist.sum() + 1e-7)  # Normalize
            
            return hist
            
        except Exception as e:
            logger.error(f"Histogram extraction failed: {e}")
            return np.zeros(HISTOGRAM_BINS * 3)
    
    def _extract_clip_features(self, image_data: bytes) -> np.ndarray:
        """
        Extract CLIP embeddings (when CLIP is available).
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            CLIP embedding vector (512 dimensions)
        """
        try:
            return self.clip_model.encode_image(image_data)
        except Exception as e:
            logger.error(f"CLIP extraction failed: {e}")
            return np.zeros(512)
    
    def _extract_huggingface_features(self, image_data: bytes) -> np.ndarray:
        """
        Extract features using Hugging Face vision model.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Feature embedding vector
        """
        from PIL import Image
        import io
        import torch
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Preprocess
            inputs = self.hf_processor(images=image, return_tensors="pt")
            
            # Move to same device as model
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Get embedding
            with torch.no_grad():
                outputs = self.hf_model(**inputs)
                # Use pooled output or last hidden state
                if hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
                    features = outputs.pooler_output
                elif hasattr(outputs, 'last_hidden_state'):
                    # Global average pooling
                    features = outputs.last_hidden_state.mean(dim=1)
                else:
                    # Fallback to first tensor output
                    features = outputs[0].mean(dim=1) if len(outputs[0].shape) > 2 else outputs[0]
            
            # Normalize
            features = features / (features.norm(dim=-1, keepdim=True) + 1e-7)
            
            # Convert to numpy
            embedding = features.cpu().numpy().flatten()
            
            logger.debug(f"Extracted HF features: shape={embedding.shape}")
            return embedding
            
        except Exception as e:
            logger.error(f"Hugging Face extraction failed: {e}")
            # Return zero vector of expected size (768 for most models)
            return np.zeros(768)
    
    def compute_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """
        Compute similarity score between two feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Similarity score (higher = more similar)
            For histograms: 0 to 1 (exponential of chi-squared)
            For CLIP/HF: -1 to 1 (cosine similarity)
        """
        if self.use_clip or self.use_huggingface:
            # Cosine similarity for deep learning embeddings
            return float(np.dot(features1, features2) / 
                        (np.linalg.norm(features1) * np.linalg.norm(features2) + 1e-7))
        else:
            # Chi-squared distance for histograms (lower is better)
            # Convert to similarity score by negating
            chi_squared = np.sum((features1 - features2) ** 2 / (features1 + features2 + 1e-7))
            # Convert to similarity: higher is better
            # Use negative exponential to convert distance to similarity
            similarity = np.exp(-chi_squared / 10)  # Scale factor for reasonable range
            return float(similarity)


def rank_dishes_by_similarity(
    query_features: np.ndarray,
    dish_features: List[Tuple[int, np.ndarray, str]],
    top_k: int = 5
) -> List[Tuple[int, float, str]]:
    """
    Rank dishes by similarity to query image.
    
    Args:
        query_features: Feature vector of query image
        dish_features: List of (dish_id, features, dish_name) tuples
        top_k: Number of top results to return
        
    Returns:
        List of (dish_id, similarity_score, dish_name) sorted by similarity (desc)
    """
    extractor = ImageFeatureExtractor(use_clip=USE_CLIP, use_huggingface=USE_HUGGINGFACE)
    
    # Compute similarities
    similarities = []
    for dish_id, features, dish_name in dish_features:
        similarity = extractor.compute_similarity(query_features, features)
        similarities.append((dish_id, similarity, dish_name))
    
    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Return top-k
    return similarities[:top_k]


# Cache for precomputed dish features (in production, use Redis or database)
_dish_features_cache: Optional[List[Tuple[int, np.ndarray, str]]] = None


def get_cached_dish_features(db_session) -> List[Tuple[int, np.ndarray, str]]:
    """
    Get or compute features for all dishes with images.
    
    In production, this should:
    1. Store features in database or Redis
    2. Update incrementally when dishes are added/modified
    3. Use a background task to precompute features
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        List of (dish_id, features, dish_name) tuples
    """
    global _dish_features_cache
    
    # For demo, use simple in-memory cache
    # In production, check Redis or database first
    if _dish_features_cache is not None:
        logger.debug(f"Using cached features for {len(_dish_features_cache)} dishes")
        return _dish_features_cache
    
    from app.models import Dish
    import os
    
    logger.info("Computing features for all dishes...")
    extractor = ImageFeatureExtractor(use_clip=USE_CLIP, use_huggingface=USE_HUGGINGFACE)
    
    # Get all dishes with images
    dishes = db_session.query(Dish).filter(Dish.picture.isnot(None)).all()
    
    dish_features = []
    for dish in dishes:
        if not dish.picture:
            continue
        
        # Determine image path
        # dish.picture can be URL or path like "/static/images/dish_1.jpg"
        if dish.picture.startswith('http'):
            # Skip external URLs for now
            logger.debug(f"Skipping external URL for dish {dish.id}")
            continue
        
        # Handle local paths
        if dish.picture.startswith('/static/'):
            # Docker path
            if os.path.exists('/app'):
                image_path = f"/app{dish.picture}"
            else:
                # Local development
                image_path = str(Path(__file__).parent.parent / dish.picture.lstrip('/'))
        else:
            image_path = dish.picture
        
        # Check if file exists
        if not os.path.exists(image_path):
            logger.warning(f"Image not found for dish {dish.id}: {image_path}")
            continue
        
        # Extract features
        try:
            features = extractor.extract_features_from_path(image_path)
            dish_features.append((dish.id, features, dish.name))
            logger.debug(f"Extracted features for dish {dish.id}: {dish.name}")
        except Exception as e:
            logger.error(f"Failed to extract features for dish {dish.id}: {e}")
    
    _dish_features_cache = dish_features
    logger.info(f"✅ Cached features for {len(dish_features)} dishes")
    
    return dish_features


def clear_dish_features_cache():
    """Clear the cached dish features (call when dishes are modified)."""
    global _dish_features_cache
    _dish_features_cache = None
    logger.info("Cleared dish features cache")
