
import DishCard from './DishCard';
import { DishCardSkeleton } from './LoadingSkeleton';
import { Dish } from '../types/api';

interface DishGridProps {
  dishes: Dish[];
  title?: string;
  emptyMessage?: string;
  onAddToCart?: (dish: Dish) => void;
  loading?: boolean;
  isVip?: boolean;
}

export default function DishGrid({
  dishes,
  title,
  emptyMessage = 'No dishes found',
  onAddToCart,
  loading = false,
  isVip = false,
}: DishGridProps) {
  if (loading) {
    return (
      <div>
        {title && <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <DishCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (dishes.length === 0) {
    return (
      <div>
        {title && <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>}
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-6xl mb-4">🍽️</div>
          <p className="text-gray-600">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {title && <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {dishes.map((dish) => (
          <DishCard key={dish.id} dish={dish} onAddToCart={onAddToCart} isVip={isVip} />
        ))}
      </div>
    </div>
  );
}
