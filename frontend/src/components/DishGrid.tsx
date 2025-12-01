import React from 'react';
import DishCard from './DishCard';
import type { Dish } from '../types/dish';
import './DishGrid.css';

interface DishGridProps {
  dishes: Dish[];
  title?: string;
  emptyMessage?: string;
  onDishClick?: (dish: Dish) => void;
  onAddToCart?: (dish: Dish) => void;
  showAddButton?: boolean;
  loading?: boolean;
}

/**
 * DishGrid Component
 * 
 * Displays a responsive grid of DishCards with optional title
 */
const DishGrid: React.FC<DishGridProps> = ({
  dishes,
  title,
  emptyMessage = 'No dishes available',
  onDishClick,
  onAddToCart,
  showAddButton = true,
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="dish-grid-container">
        {title && <h2 className="dish-grid-title">{title}</h2>}
        <div className="dish-grid loading">
          {[1, 2, 3].map((i) => (
            <div key={i} className="dish-card-skeleton">
              <div className="skeleton-image"></div>
              <div className="skeleton-content">
                <div className="skeleton-line title"></div>
                <div className="skeleton-line"></div>
                <div className="skeleton-line short"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (dishes.length === 0) {
    return (
      <div className="dish-grid-container">
        {title && <h2 className="dish-grid-title">{title}</h2>}
        <div className="dish-grid-empty">
          <p>{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dish-grid-container">
      {title && <h2 className="dish-grid-title">{title}</h2>}
      <div className="dish-grid">
        {dishes.map((dish) => (
          <DishCard
            key={dish.id}
            dish={dish}
            onClick={onDishClick}
            onAddToCart={onAddToCart}
            showAddButton={showAddButton}
          />
        ))}
      </div>
    </div>
  );
};

export default DishGrid;
