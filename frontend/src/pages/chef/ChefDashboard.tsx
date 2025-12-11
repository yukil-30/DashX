import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import { Dish } from '../../types/api';
import { DishGrid } from '../../components';
import { useAuth } from '../../contexts/AuthContext';
// local helper for building image URLs

export default function ChefDashboard() {
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [loading, setLoading] = useState(true);
  

const { user } = useAuth();

useEffect(() => {
  if (user) fetchChefDishes();
}, [user]);

  const fetchChefDishes = async () => {
  if (!user) return;
    try {
      // Fetch user's own dishes - has chef_id filter
      const response = await apiClient.get(`/dishes?per_page=50&chef_id=${user.ID}`);
      setDishes(response.data.dishes);
    } catch (err) {
      console.error('Failed to fetch dishes:', err);
    } finally {
      setLoading(false);
    }
  };
  // Helper to build full image URLs (local version)
  const getImageUrl = (path?: string | null) => {
    if (!path) return '';
    const backendUrl = 'http://localhost:8000';
    return `${backendUrl}/${encodeURI(path.replace(/^\/+/, ''))}`;
  };

  // Map dishes with full image URLs **just before passing to DishGrid**
  const dishesWithFullUrl = dishes.map((d: Dish) => ({
    ...d,
    picture: getImageUrl(d.picture),
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Chef Dashboard</h1>
          <p className="text-gray-600">Manage your menu items</p>
        </div>
        <div className="flex gap-3">
          <Link to="/chef/complaints" className="btn-secondary">
            View Complaints
          </Link>
          <Link to="/chef/dishes/new" className="btn-primary">
            + Add New Dish
          </Link>
        </div>
      </div>

      {/* Quick link to chef orders (use the nav to access full Active Orders page) */}

      <DishGrid
        dishes={dishesWithFullUrl}
        loading={loading}
        emptyMessage="No dishes yet. Create your first dish!"
      />
    </div>
  );
}
