import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiClient from '../lib/api-client';
import { Dish, DishReview } from '../types/api';
import { ImageCarousel, RatingStars } from '../components';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import toast from 'react-hot-toast';

interface DishReviewListResponse {
  reviews: DishReview[];
  total: number;
  average_rating: number;
}

export default function DishDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToCart } = useCart();
  const [dish, setDish] = useState<Dish | null>(null);
  const [reviews, setReviews] = useState<DishReview[]>([]);
  const [reviewsTotal, setReviewsTotal] = useState(0);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // ✅ Helper to check if user can order
  const isCustomerOrVip = user?.type === 'customer' || user?.type === 'vip';

  useEffect(() => {
    if (id) {
      fetchDish();
      fetchReviews();
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

  const fetchReviews = async () => {
    setReviewsLoading(true);
    try {
      const response = await apiClient.get<DishReviewListResponse>(`/reviews/dish/${id}`);
      setReviews(response.data.reviews);
      setReviewsTotal(response.data.total);
    } catch (err: any) {
      console.error('Failed to load reviews:', err);
    } finally {
      setReviewsLoading(false);
    }
  };

  const handleAddToCart = () => {
    if (dish) {
      addToCart(dish, quantity);
      toast.success(`Added ${quantity} ${dish.name} to cart!`);
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
      <button
        onClick={() => navigate(-1)}
        className="mb-6 text-gray-600 hover:text-gray-900 flex items-center gap-2"
      >
        ← Back
      </button>

      <div className="grid md:grid-cols-2 gap-12">
        <div>
          <ImageCarousel
            images={dish.picture ? [dish.picture] : []}
            alt={dish.name}
          />
        </div>

        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">{dish.name}</h1>

          <div className="flex items-center gap-4 mb-6">
            <RatingStars rating={dish.average_rating} size="lg" />
            <span className="text-gray-600">
              ({dish.reviews} {dish.reviews === 1 ? 'review' : 'reviews'})
            </span>
          </div>

          <div className="mb-6">
            <span className="text-4xl font-bold text-primary-600">
              {dish.cost_formatted}
            </span>
          </div>

          {dish.description && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
              <p className="text-gray-700 leading-relaxed">{dish.description}</p>
            </div>
          )}

          {/* ✅ FIXED: Allow both customers and VIPs to add to cart */}
          {isCustomerOrVip && (
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

          {dish.chefID && (
            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Chef Information</h3>
              <p className="text-gray-600">Chef ID: {dish.chefID}</p>
            </div>
          )}
        </div>
      </div>

      <div className="mt-16 border-t pt-12">
        <h2 className="text-3xl font-bold text-gray-900 mb-8">
          Customer Reviews ({reviewsTotal})
        </h2>
        
        {reviewsLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : reviews.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-xl">
            <p className="text-gray-500 text-lg mb-2">No reviews yet</p>
            <p className="text-gray-400">Be the first to review this dish after ordering!</p>
          </div>
        ) : (
          <div className="space-y-6">
            {reviews.map((review) => (
              <div key={review.id} className="bg-white rounded-xl shadow-md p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="font-semibold text-gray-900">
                      {review.reviewer_email || 'Anonymous'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(review.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </p>
                  </div>
                  <RatingStars rating={review.rating} size="md" />
                </div>
                {review.review_text && (
                  <p className="text-gray-700">{review.review_text}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}