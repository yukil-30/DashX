import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../lib/api-client';
import { ChefProfile } from '../types/api';
import { RatingStars } from '../components';

export default function ChefsListPage() {
  const [chefs, setChefs] = useState<ChefProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChefs();
  }, []);

  const fetchChefs = async () => {
    try {
      const response = await apiClient.get<ChefProfile[] | { chefs: ChefProfile[] }>('/profiles/chefs');
      // Handle both array and wrapped response shapes
      const data = response.data;
      if (Array.isArray(data)) {
        setChefs(data);
      } else if (data && Array.isArray(data.chefs)) {
        setChefs(data.chefs);
      } else {
        setChefs([]);
      }
    } catch (err: any) {
      toast.error('Failed to load chefs');
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Our Chefs</h1>
        <p className="text-gray-600 mt-2">
          Meet the talented chefs behind our delicious dishes
        </p>
      </div>

      {chefs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl shadow-md">
          <div className="text-6xl mb-4">👨‍🍳</div>
          <p className="text-gray-600 text-xl">No chefs found</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {chefs.map((chef) => (
            <Link
              key={chef.account_id}
              to={`/profiles/chefs/${chef.account_id}`}
              className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow"
            >
              <div className="bg-gradient-to-r from-amber-500 to-orange-500 h-16"></div>
              <div className="p-6 -mt-8">
                <img
                  src={chef.profile_picture || '/images/chef-placeholder.svg'}
                  alt={chef.display_name || 'Chef'}
                  className="w-16 h-16 rounded-full border-2 border-white shadow-md object-cover mx-auto"
                />
                <div className="text-center mt-3">
                  <h3 className="font-semibold text-gray-900">
                    {chef.display_name || chef.email}
                  </h3>
                  {chef.specialty && (
                    <p className="text-sm text-gray-500">{chef.specialty}</p>
                  )}
                  <div className="flex items-center justify-center gap-2 mt-2">
                    <RatingStars rating={chef.average_dish_rating} size="sm" />
                    <span className="text-sm text-gray-600">
                      {chef.average_dish_rating.toFixed(1)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {chef.dishes_created} dishes
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
