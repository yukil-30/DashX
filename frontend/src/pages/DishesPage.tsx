import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import apiClient from '../lib/api-client';
import { DishListResponse } from '../types/api';
import { DishGrid } from '../components';
import { useAuth } from '../contexts/AuthContext';

export default function DishesPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<DishListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const page = parseInt(searchParams.get('page') || '1', 10);
  const search = searchParams.get('q') || '';
  const orderBy = searchParams.get('order_by') || 'popular';
  const [searchInput, setSearchInput] = useState(search);

  useEffect(() => {
    fetchDishes();
  }, [page, search, orderBy]);

  const fetchDishes = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '20',
        order_by: orderBy,
      });
      if (search) params.append('q', search);

      const response = await apiClient.get<DishListResponse>(`/dishes?${params}`);
      setData(response.data);
      setError('');
    } catch (err: any) {
      setError('Failed to load dishes');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams(searchParams);
    if (searchInput) {
      params.set('q', searchInput);
    } else {
      params.delete('q');
    }
    params.set('page', '1');
    setSearchParams(params);
  };

  const handleOrderChange = (newOrder: string) => {
    const params = new URLSearchParams(searchParams);
    params.set('order_by', newOrder);
    params.set('page', '1');
    setSearchParams(params);
  };

  const goToPage = (newPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', newPage.toString());
    setSearchParams(params);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Determine the empty message based on the current sort option
  const getEmptyMessage = () => {
    if (orderBy === 'past_orders') {
      if (!user) {
        return 'Please log in to view your past orders';
      }
      return "You haven't ordered any dishes yet";
    }
    if (search) {
      return `No dishes found for "${search}"`;
    }
    return 'No dishes available';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Menu</h1>

        {/* Search and Filter Bar */}
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search dishes..."
                className="input-field pr-24"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-1.5 px-4"
              >
                Search
              </button>
            </div>
          </form>

          {/* Sort */}
          <select
            value={orderBy}
            onChange={(e) => handleOrderChange(e.target.value)}
            className="input-field md:w-48"
          >
            <option value="popular">Most Popular</option>
            <option value="rating">Highest Rated</option>
            <option value="cost">Price: Low to High</option>
            <option value="newest">Newest</option>
            <option value="past_orders">Past Orders</option>
          </select>
        </div>

        {/* Results info */}
        {data && (
          <div className="mt-4 text-gray-600">
            {orderBy === 'past_orders' && data.total === 0 ? (
              <span>{getEmptyMessage()}</span>
            ) : (
              <>
                Showing {data.dishes.length} of {data.total} dishes
                {search && ` for "${search}"`}
                {orderBy === 'past_orders' && ' from your past orders'}
              </>
            )}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 mb-6">
          {error}
        </div>
      )}

      {/* Dishes Grid */}
      <DishGrid
        dishes={data?.dishes || []}
        loading={loading}
        emptyMessage={getEmptyMessage()}
        onAddToCart={user?.type === 'customer' ? (dish) => {
          console.log('Add to cart:', dish);
        } : undefined}
      />

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="mt-12 flex justify-center items-center gap-2">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page === 1}
            className="btn-secondary disabled:opacity-30"
          >
            ← Previous
          </button>

          <div className="flex gap-2">
            {Array.from({ length: Math.min(data.total_pages, 5) }, (_, i) => {
              let pageNum;
              if (data.total_pages <= 5) {
                pageNum = i + 1;
              } else if (page <= 3) {
                pageNum = i + 1;
              } else if (page >= data.total_pages - 2) {
                pageNum = data.total_pages - 4 + i;
              } else {
                pageNum = page - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => goToPage(pageNum)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    page === pageNum
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => goToPage(page + 1)}
            disabled={page === data.total_pages}
            className="btn-secondary disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}