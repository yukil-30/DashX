import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../lib/api-client';
import { HomeResponse } from '../types/api';
import { DishGrid } from '../components';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import toast from 'react-hot-toast';

export default function HomePage() {
  const { user } = useAuth();
  const { addToCart } = useCart();
  const [data, setData] = useState<HomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchHomeData();
  }, [user]);

  const fetchHomeData = async () => {
    try {
      const response = await apiClient.get<HomeResponse>('/home');
      setData(response.data);
    } catch (err: any) {
      setError('Failed to load home page');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = (dish: any) => {
    addToCart(dish, 1);
    toast.success(`${dish.name} added to cart!`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="mb-12 text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
          Welcome to DashX Restaurant 🍽️
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          {data?.is_personalized
            ? 'Your personalized dining recommendations'
            : 'Discover our most popular dishes'}
        </p>
        <div className="flex gap-4 justify-center">
          <Link to="/dishes" className="btn-primary text-lg px-8">
            Browse Menu
          </Link>
          {user && user.type === 'customer' && (
            <Link to="/cart" className="btn-secondary text-lg px-8">
              View Cart
            </Link>
          )}
        </div>
      </div>

      {/* Most Ordered / Popular Section */}
      {data && data.most_ordered.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-3xl font-bold text-gray-900">
              {data.is_personalized ? '🎯 Your Favorites' : '🔥 Most Popular'}
            </h2>
            <Link to="/dishes?order_by=popular" className="text-primary-600 hover:text-primary-700 font-medium">
              View all →
            </Link>
          </div>
          <DishGrid
            dishes={data.most_ordered}
            onAddToCart={user?.type === 'customer' ? handleAddToCart : undefined}
          />
        </section>
      )}

      {/* Top Rated Section */}
      {data && data.top_rated.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-3xl font-bold text-gray-900">
              ⭐ Top Rated
            </h2>
            <Link to="/dishes?order_by=rating" className="text-primary-600 hover:text-primary-700 font-medium">
              View all →
            </Link>
          </div>
          <DishGrid
            dishes={data.top_rated}
            onAddToCart={user?.type === 'customer' ? handleAddToCart : undefined}
          />
        </section>
      )}

      {/* Features Section */}
      <section className="mt-16 grid md:grid-cols-3 gap-8">
        <div className="text-center p-6 bg-white rounded-xl shadow-md">
          <div className="text-4xl mb-4">🚚</div>
          <h3 className="text-xl font-semibold mb-2">Fast Delivery</h3>
          <p className="text-gray-600">Competitive bidding ensures best delivery rates</p>
        </div>
        <div className="text-center p-6 bg-white rounded-xl shadow-md">
          <div className="text-4xl mb-4">⭐</div>
          <h3 className="text-xl font-semibold mb-2">Quality Assured</h3>
          <p className="text-gray-600">Rate your dishes and help others choose</p>
        </div>
        <div className="text-center p-6 bg-white rounded-xl shadow-md">
          <div className="text-4xl mb-4">💬</div>
          <h3 className="text-xl font-semibold mb-2">24/7 Support</h3>
          <p className="text-gray-600">AI-powered chat support always available</p>
        </div>
      </section>
    </div>
  );
}