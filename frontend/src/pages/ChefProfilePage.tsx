import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../lib/api-client';
import { ChefProfile } from '../types/api';
import { DishCard, RatingStars } from '../components';

export default function ChefProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [chef, setChef] = useState<ChefProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchChefProfile();
    }
  }, [id]);

  const fetchChefProfile = async () => {
    try {
      const response = await apiClient.get<ChefProfile>(`/profiles/chefs/${id}`);
      // Transform dish image URLs to use backend URL
      const chefData = response.data;
      if (chefData.dishes) {
        chefData.dishes = chefData.dishes.map(dish => ({
          ...dish,
          picture: dish.picture
            ? `http://localhost:8000/${encodeURI(dish.picture.replace(/^\/+/, ''))}`
            : null
        }));
      }
      setChef(chefData);
    } catch (err: any) {
      toast.error('Chef not found');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!chef) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600 text-xl">Chef not found</p>
        <Link to="/dishes" className="btn-primary mt-4 inline-block">
          Browse Menu
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Chef Profile Header */}
      <div className="bg-white rounded-xl shadow-md overflow-hidden mb-8">
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 h-32"></div>
        <div className="px-6 pb-6">
          <div className="flex flex-col md:flex-row items-center md:items-end gap-6 -mt-16">
            <img
              src={chef.profile_picture || '/images/chef-placeholder.svg'}
              alt={chef.display_name || 'Chef'}
              className="w-32 h-32 rounded-full border-4 border-white shadow-lg object-cover"
            />
            <div className="flex-1 text-center md:text-left">
              <h1 className="text-3xl font-bold text-gray-900">
                {chef.display_name || chef.email}
              </h1>
              {chef.specialty && (
                <p className="text-lg text-gray-600 mt-1">
                  🍳 Specialty: {chef.specialty}
                </p>
              )}
              {chef.bio && (
                <p className="text-gray-500 mt-2">{chef.bio}</p>
              )}
            </div>
            <div className="text-center md:text-right">
              <div className="flex items-center justify-center md:justify-end gap-2">
                <RatingStars rating={chef.average_dish_rating} size="lg" />
                <span className="text-lg font-medium text-gray-700">
                  {chef.average_dish_rating.toFixed(1)}
                </span>
              </div>
              <p className="text-gray-500">
                {chef.total_reviews_given || 0} reviews
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl shadow-md p-6 text-center">
          <p className="text-4xl font-bold text-primary-600">{chef.dishes_created}</p>
          <p className="text-gray-600">Dishes Created</p>
        </div>
        <div className="bg-white rounded-xl shadow-md p-6 text-center">
          <p className="text-4xl font-bold text-amber-600">
            {chef.average_dish_rating.toFixed(1)}
          </p>
          <p className="text-gray-600">Average Rating</p>
        </div>
        <div className="bg-white rounded-xl shadow-md p-6 text-center">
          <p className="text-4xl font-bold text-green-600">
            {chef.total_orders || 0}
          </p>
          <p className="text-gray-600">Orders Fulfilled</p>
        </div>
      </div>

      {/* Chef's Dishes */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Dishes by {chef.display_name || 'this Chef'}
        </h2>
        {chef.dishes && chef.dishes.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {chef.dishes.map((dish) => (
              <DishCard key={dish.id} dish={dish} />
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 rounded-xl p-8 text-center">
            <p className="text-gray-600">No dishes yet</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-center gap-4">
        <Link to="/profiles/chefs" className="btn-secondary">
          View All Chefs
        </Link>
        <Link to="/dishes" className="btn-primary">
          Browse Menu
        </Link>
      </div>
    </div>
  );
}
