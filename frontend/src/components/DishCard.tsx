import React from 'react';
import type { Dish } from '../types/dish';
import './DishCard.css';

interface DishCardProps {
  dish: Dish;
  onAddToCart?: (dish: Dish) => void;
  onClick?: (dish: Dish) => void;
  showAddButton?: boolean;
}

/**
 * Star rating display component
 */
const StarRating: React.FC<{ rating: number; reviewCount?: number }> = ({ rating, reviewCount }) => {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 >= 0.5;
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

  return (
    <div className="star-rating" title={`${rating.toFixed(1)} out of 5 stars`}>
      <span className="stars">
        {'★'.repeat(fullStars)}
        {hasHalfStar && '½'}
        {'☆'.repeat(emptyStars)}
      </span>
      {reviewCount !== undefined && (
        <span className="review-count">({reviewCount})</span>
      )}
    </div>
  );
};

/**
 * DishCard Component
 * 
 * Displays a dish with:
 * - Image (with fallback)
 * - Name and description
 * - Price formatted as currency
 * - Star rating with review count
 * - Availability badge
 * - Special badge for featured items
 */
const DishCard: React.FC<DishCardProps> = ({ 
  dish, 
  onAddToCart, 
  onClick,
  showAddButton = true 
}) => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  // Get image URL - use first image from images array, or picture, or fallback
  const imageUrl = dish.images?.[0]?.image_url || dish.picture;
  const fullImageUrl = imageUrl 
    ? imageUrl.startsWith('http') 
      ? imageUrl 
      : `${apiUrl}${imageUrl}`
    : '/placeholder-dish.svg';

  const handleClick = () => {
    if (onClick) {
      onClick(dish);
    }
  };

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering card click
    if (onAddToCart) {
      onAddToCart(dish);
    }
  };

  return (
    <div 
      className={`dish-card ${!dish.is_available ? 'unavailable' : ''} ${dish.is_special ? 'special' : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
    >
      {/* Image Section */}
      <div className="dish-image-container">
        <img 
          src={fullImageUrl}
          alt={dish.name}
          className="dish-image"
          loading="lazy"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.src = '/placeholder-dish.svg';
          }}
        />
        {dish.is_special && (
          <span className="badge special-badge">⭐ Special</span>
        )}
        {!dish.is_available && (
          <div className="unavailable-overlay">
            <span>Currently Unavailable</span>
          </div>
        )}
      </div>

      {/* Content Section */}
      <div className="dish-content">
        <div className="dish-header">
          <h3 className="dish-name">{dish.name}</h3>
          {dish.category && (
            <span className="dish-category">{dish.category}</span>
          )}
        </div>

        {dish.description && (
          <p className="dish-description">{dish.description}</p>
        )}

        {/* Rating */}
        {dish.review_count > 0 && (
          <StarRating rating={dish.average_rating} reviewCount={dish.review_count} />
        )}

        {/* Price and Action */}
        <div className="dish-footer">
          <span className="dish-price">{dish.price_formatted}</span>
          
          {showAddButton && dish.is_available && onAddToCart && (
            <button 
              className="add-to-cart-btn"
              onClick={handleAddToCart}
              aria-label={`Add ${dish.name} to cart`}
            >
              Add to Cart
            </button>
          )}
        </div>

        {/* Popularity indicator */}
        {dish.order_count > 10 && (
          <div className="popularity-indicator">
            🔥 Popular - {dish.order_count} orders
          </div>
        )}
      </div>
    </div>
  );
};

export default DishCard;
