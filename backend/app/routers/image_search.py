"""
Image Search Router - Visual food search functionality

Endpoints:
- POST /image-search - Upload food image and get similar dishes
- POST /image-search/precompute - Admin endpoint to precompute all dish features
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dish
from app.schemas import DishResponse
from app.image_utils import (
    ImageFeatureExtractor,
    get_cached_dish_features,
    rank_dishes_by_similarity,
    clear_dish_features_cache,
    USE_CLIP,
    USE_HUGGINGFACE
)
from app.auth import get_current_user, require_manager
from app.models import Account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-search", tags=["Image Search"])

# Supported image formats
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image_file(file: UploadFile) -> None:
    """
    Validate uploaded image file.
    
    Args:
        file: Uploaded file
        
    Raises:
        HTTPException: If file is invalid
    """
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Check extension
    filename = file.filename or ""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image format not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post("", response_model=List[DishResponse])
async def search_by_image(
    file: UploadFile = File(..., description="Food image to search for"),
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Search for dishes by uploading a food image.
    
    This endpoint:
    1. Accepts an uploaded image
    2. Extracts visual features (color histogram or CLIP embeddings)
    3. Compares against all dishes in database
    4. Returns top-5 most similar dishes
    **Current Implementation:**
    - Uses Hugging Face vision model (nateraw/food)
    - Food-specific embeddings for better accuracy
    
    **Alternative Methods:**
    - Histogram: Set `USE_HUGGINGFACE = False` (fastest, basic)
    - CLIP: Set `USE_CLIP = True` (best semantic understanding)se up clip-service`
    - Much better semantic similarity
    
    Args:
        file: Uploaded image file (JPEG, PNG, etc.)
        top_k: Number of results to return (default: 5)
        
    Returns:
        List of top matching dishes with similarity scores
    """
    # Validate file
    validate_image_file(file)
    
    # Read image data
    try:
        image_data = await file.read()
        
        # Check file size
        if len(image_data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        logger.info(f"Received image search request from user {current_user.ID}: "
                   f"{len(image_data)} bytes, filename={file.filename}")
        
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read image file"
        )
    
    # Extract features from query image
    extractor = ImageFeatureExtractor(use_clip=USE_CLIP, use_huggingface=USE_HUGGINGFACE)
    try:
        query_features = extractor.extract_features(image_data)
        logger.debug(f"Extracted query features: shape={query_features.shape}")
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process image"
        )
    
    # Get cached dish features
    try:
        dish_features = get_cached_dish_features(db)
        
        if not dish_features:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No dishes with images found in database"
            )
        
        logger.info(f"Comparing against {len(dish_features)} dishes")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dish features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dish database"
        )
    
    # Rank dishes by similarity
    try:
        results = rank_dishes_by_similarity(query_features, dish_features, top_k=top_k)
        logger.info(f"Found {len(results)} matching dishes")
        
        # Log top results for debugging
        for i, (dish_id, score, name) in enumerate(results[:3], 1):
            logger.debug(f"  {i}. {name} (ID={dish_id}, score={score:.4f})")
        
    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute similarities"
        )
    
    # Fetch full dish details
    dish_ids = [dish_id for dish_id, _, _ in results]
    dishes = db.query(Dish).filter(Dish.id.in_(dish_ids)).all()
    
    # Create dish lookup
    dish_lookup = {dish.id: dish for dish in dishes}
    
    # Build response with scores
    response = []
    for dish_id, score, _ in results:
        if dish_id in dish_lookup:
            dish = dish_lookup[dish_id]
            dish_response = DishResponse(
                id=dish.id,
                name=dish.name,
                description=dish.description,
                cost=dish.cost,
                cost_formatted=f"${dish.cost / 100:.2f}",
                picture=dish.picture,
                average_rating=float(dish.average_rating or 0),
                reviews=dish.reviews,
                chefID=dish.chefID,
                restaurantID=dish.restaurantID
            )
            # Add similarity score as extra field
            dish_response.__dict__['similarity_score'] = round(score, 4)
            response.append(dish_response)
    
    return response


@router.post("/precompute")
async def precompute_dish_features(
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Precompute and cache features for all dishes.
    
    This is useful when:
    - New dishes are added
    - Switching between histogram and CLIP mode
    - Initializing the system
    
    Manager only.
    
    Returns:
        Status message with count of processed dishes
    """
    logger.info(f"Manager {current_user.ID} triggered feature precomputation")
    
    # Clear existing cache
    clear_dish_features_cache()
    
    # Recompute features
    try:
        dish_features = get_cached_dish_features(db)
        count = len(dish_features)
        count = len(dish_features)
        
        if USE_CLIP:
            method = "CLIP embeddings"
        elif USE_HUGGINGFACE:
            method = "Hugging Face vision model"
        else:
            method = "color histograms"
        return {
            "message": f"Successfully precomputed features for {count} dishes",
            "method": method,
            "dish_count": count
        }
        
    except Exception as e:
        logger.error(f"Precomputation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to precompute features: {str(e)}"
        )


@router.get("/status")
async def get_search_status(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Get status of image search system.
    
    Returns:
        Information about available dishes, feature extraction method, etc.
    """
    from app.models import Dish
    from app.image_utils import _dish_features_cache
    
    # Count dishes with images
    total_dishes = db.query(Dish).count()
    dishes_with_images = db.query(Dish).filter(Dish.picture.isnot(None)).count()
    cached_count = len(_dish_features_cache) if _dish_features_cache else 0
    
    # Determine method
    if USE_CLIP:
        method = "CLIP embeddings"
    elif USE_HUGGINGFACE:
        method = "Hugging Face vision model"
    else:
        method = "color histograms"
    
    return {
        "method": method,
        "total_dishes": total_dishes,
        "dishes_with_images": dishes_with_images,
        "cached_features": cached_count,
        "ready": cached_count > 0,
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "supported_formats": list(ALLOWED_EXTENSIONS)
    }
