import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiClient from '../lib/api-client';
import { Dish } from '../types/api';
import { ImageCarousel, RatingStars } from '../components';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';

export default function DishDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToCart } = useCart();
  const [dish, setDish] = useState<Dish | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) {
      fetchDish();
    }
  }, [id]);

  const fetchDish = async () => {
    try {
      const response = await apiClient.get<Dish>(`/dishes/${id}`);
      setDish(response.data);
    } catch (err: any) {
      setError('Failed to load dish details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = () => {
    if (dish) {
      addToCart(dish, quantity);
      // Show success message or navigate to cart
      alert(`Added ${quantity} ${dish.name} to cart!`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error || !dish) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error || 'Dish not found'}
        </div>
        <Link to="/dishes" className="btn-primary mt-4 inline-block">
          Back to Menu
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="mb-6 text-gray-600 hover:text-gray-900 flex items-center gap-2"
      >
        ← Back
      </button>

      <div className="grid md:grid-cols-2 gap-12">
        {/* Image */}
        <div>
          <ImageCarousel
            images={dish.picture ? [dish.picture] : []}
            alt={dish.name}
          />
        </div>

        {/* Details */}
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">{dish.name}</h1>

          {/* Rating */}
          <div className="flex items-center gap-4 mb-6">
            <RatingStars rating={dish.average_rating} size="lg" />
            <span className="text-gray-600">
              ({dish.reviews} {dish.reviews === 1 ? 'review' : 'reviews'})
            </span>
          </div>

          {/* Price */}
          <div className="mb-6">
            <span className="text-4xl font-bold text-primary-600">
              {dish.cost_formatted}
            </span>
          </div>

          {/* Description */}
          {dish.description && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
              <p className="text-gray-700 leading-relaxed">{dish.description}</p>
            </div>
          )}

          {/* Add to Cart */}
          {user?.type === 'customer' && (
            <div className="mb-8">
              <div className="flex items-center gap-4 mb-4">
                <label htmlFor="quantity" className="text-gray-700 font-medium">
                  Quantity:
                </label>
                <div className="flex items-center border border-gray-300 rounded-lg">
                  <button
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-l-lg"
                  >
                    −
                  </button>
                  <input
                    id="quantity"
                    type="number"
                    min="1"
                    max="100"
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-20 text-center border-x border-gray-300 py-2 outline-none"
                  />
                  <button
                    onClick={() => setQuantity(Math.min(100, quantity + 1))}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-r-lg"
                  >
                    +
                  </button>
                </div>
              </div>

              <button onClick={handleAddToCart} className="btn-primary w-full text-lg py-3">
                Add to Cart
              </button>
            </div>
          )}

          {!user && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <p className="text-yellow-800">
                <Link to="/auth/login" className="font-semibold underline">
                  Sign in
                </Link>{' '}
                to add items to your cart
              </p>
            </div>
          )}

          {/* Chef Info */}
          {dish.chefID && (
            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Chef Information</h3>
              <p className="text-gray-600">Chef ID: {dish.chefID}</p>
            </div>
          )}
        </div>
      </div>

      {/* Reviews Section - Placeholder for future implementation */}
      <div className="mt-16 border-t pt-12">
        <h2 className="text-3xl font-bold text-gray-900 mb-8">Customer Reviews</h2>
        <div className="text-center py-8 text-gray-500">
          Reviews feature coming soon...
        </div>
      </div>
    </div>
  );
}
