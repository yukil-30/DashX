import { Link } from 'react-router-dom';
import { Dish } from '../types/api';
import RatingStars from './RatingStars';

interface DishCardProps {
  dish: Dish;
  onAddToCart?: (dish: Dish) => void;
}

export default function DishCard({ dish, onAddToCart }: DishCardProps) {
  return (
    <div className="card group" data-testid="dish-card">
      {/* Image */}
      <div className="relative h-48 bg-gray-200 overflow-hidden">
        {dish.picture ? (
          <img
            src={dish.picture}
            alt={dish.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-200 to-gray-300">
            <span className="text-6xl">🍽️</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <Link to={`/dishes/${dish.id}`}>
          <h3 className="text-lg font-semibold text-gray-900 mb-1 hover:text-primary-600 transition-colors line-clamp-1">
            {dish.name}
          </h3>
        </Link>

        {dish.description && (
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
            {dish.description}
          </p>
        )}

        <div className="flex items-center justify-between mb-3">
          <span className="text-2xl font-bold text-primary-600">
            {dish.cost_formatted}
          </span>
          <div className="flex flex-col items-end">
            <RatingStars rating={dish.average_rating} size="sm" />
            <span className="text-xs text-gray-500 mt-1">
              {dish.reviews} {dish.reviews === 1 ? 'review' : 'reviews'}
            </span>
          </div>
        </div>

        {/* No VIP info shown on dish cards per design */}

        {onAddToCart && (
          <button
            onClick={() => onAddToCart(dish)}
            className="btn-primary w-full"
          >
            Add to Cart
          </button>
        )}
      </div>
    </div>
  );
}
