import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import apiClient from '../../lib/api-client';
import { CustomerDashboardResponse, DepositResponse } from '../../types/api';
import { DishCard, RatingStars } from '../../components';

interface CustomerReviewAboutMe {
  id: number;
  order_id: number;
  reviewer_email: string;
  rating: number;
  review_text: string | null;
  was_polite: boolean | null;
  easy_to_find: boolean | null;
  created_at: string | null;
}

interface ReviewsAboutMeResponse {
  reviews: CustomerReviewAboutMe[];
  total: number;
  average_rating: number | null;
}

export default function CustomerDashboard() {
  const { user, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<CustomerDashboardResponse | null>(null);
  const [reviewsAboutMe, setReviewsAboutMe] = useState<ReviewsAboutMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [depositAmount, setDepositAmount] = useState('');
  const [depositing, setDepositing] = useState(false);
  const [deregisterInProgress, setDeregisterInProgress] = useState(false);

  useEffect(() => {
    fetchDashboard();
    fetchReviewsAboutMe();
    // Also refresh user profile to get latest VIP status
    refreshProfile();
  }, []);

  const fetchReviewsAboutMe = async () => {
    try {
      const response = await apiClient.get<ReviewsAboutMeResponse>('/reviews/about-me');
      setReviewsAboutMe(response.data);
    } catch (err) {
      console.error('Failed to fetch reviews about me:', err);
    }
  };

  const fetchDashboard = async () => {
    try {
      const response = await apiClient.get<CustomerDashboardResponse>('/customer/dashboard');
      setDashboard(response.data);
      
      // Check if user just became VIP and show celebration
      if (response.data.vip_status.is_vip && !user?.type.includes('vip')) {
        toast.success('🎉 Congratulations! You are now a VIP member!', {
          duration: 5000,
          icon: '👑'
        });
      }
    } catch (err: any) {
      setError('Failed to load dashboard');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
const getBackendImage = (path: string | null) =>
  path ? `http://localhost:8000/${encodeURI(path.replace(/^\/+/, ''))}` : '/images/placeholder.png';

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    setDepositing(true);
    try {
      const amountCents = Math.round(amount * 100);
      const response = await apiClient.post<DepositResponse>('/account/deposit', {
        amount_cents: amountCents,
      });
      toast.success(`Deposited ${response.data.new_balance_formatted}`);
      setDepositAmount('');
      fetchDashboard();
      refreshProfile();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Deposit failed');
    } finally {
      setDepositing(false);
    }
  };

  const handleDeregister = async () => {
    if (!confirm('Are you sure you want to deregister your account? This will be sent to the manager for approval.')) {
      return;
    }

    setDeregisterInProgress(true);
    try {
      const response = await apiClient.post('/account/deregister');
      toast.success('Deregistration request submitted. Manager will review and close your account.');
      // Optionally redirect after deregistering
      setTimeout(() => navigate('/'), 2000);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit deregistration request');
    } finally {
      setDeregisterInProgress(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error || 'Failed to load dashboard'}
        </div>
      </div>
    );
  }

  const { vip_status } = dashboard;
  const isVIP = vip_status.is_vip || user?.type === 'vip';
  const userWarnings = user?.warnings || 0;
  const warningThreshold = isVIP ? 2 : 3;
  const showWarning = userWarnings > 0;

  // Free delivery progress: compute number of completed orders modulo 3 (0..2)
  // We only show the spark-bar when there are NO free delivery credits available.
  const FREE_DELIVERY_TARGET = 3;
  const completedOrders = vip_status.completed_orders || 0;
  const freeDeliveryCredits = vip_status.free_delivery_credits || 0;
  const freeDeliveryProgress = completedOrders % FREE_DELIVERY_TARGET; // 0..2 (filled slots)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Customer Dashboard</h1>
        <p className="text-gray-600 mt-2">Welcome back, {dashboard.email}</p>
      </div>

      {/* Warnings Banner */}
      {showWarning && (
        <div className={`mb-8 rounded-xl p-6 shadow-lg border-2 ${
          userWarnings >= warningThreshold
            ? 'bg-red-50 border-red-300'
            : 'bg-yellow-50 border-yellow-300'
        }`}>
          <div className="flex items-center gap-4">
            <span className="text-5xl">{userWarnings >= warningThreshold ? '🚨' : '⚠️'}</span>
            <div className="flex-1">
              <h3 className={`text-2xl font-bold mb-2 ${
                userWarnings >= warningThreshold ? 'text-red-800' : 'text-yellow-800'
              }`}>
                {userWarnings >= warningThreshold
                  ? 'Account Status Warning'
                  : 'You Have Warnings'}
              </h3>
              <p className={userWarnings >= warningThreshold ? 'text-red-700 mb-2' : 'text-yellow-700 mb-2'}>
                {userWarnings} warning{userWarnings === 1 ? '' : 's'} 
                {isVIP ? ' (VIPs with 2 warnings are demoted to customer)' : ' (customers with 3 warnings are deregistered)'}
              </p>
              {userWarnings >= warningThreshold && (
                <p className={`text-sm ${userWarnings >= warningThreshold ? 'text-red-600' : 'text-yellow-600'}`}>
                  {isVIP
                    ? 'You are at risk of being demoted to a regular customer. Please maintain your account in good standing.'
                    : 'One more warning will result in your account being deregistered. Please ensure you have sufficient funds before placing orders.'}
                </p>
              )}
              {userWarnings < warningThreshold && (
                <p className="text-sm text-yellow-600">
                  You received this warning for attempting to place an order without sufficient funds. {warningThreshold - userWarnings} more warning{warningThreshold - userWarnings === 1 ? '' : 's'} will result in {isVIP ? 'demotion to customer' : 'account deregistration'}.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* VIP Upgrade Banner (if just became eligible or recently upgraded) */}
      {vip_status.vip_eligible && !isVIP && (
        <div className="mb-8 bg-gradient-to-r from-amber-50 to-yellow-50 border-2 border-amber-300 rounded-xl p-6 shadow-lg">
          <div className="flex items-center gap-4">
            <span className="text-5xl">👑</span>
            <div className="flex-1">
              <h3 className="text-2xl font-bold text-amber-800 mb-2">
                You're Eligible for VIP Status!
              </h3>
              <p className="text-amber-700 mb-3">{vip_status.vip_reason}</p>
              <p className="text-sm text-amber-600">
                Complete your next order to unlock VIP benefits: 5% discount on orders + free delivery!
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Just Upgraded to VIP Banner */}
      {isVIP && vip_status.completed_orders === 3 && (
        <div className="mb-8 bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300 rounded-xl p-6 shadow-lg">
          <div className="flex items-center gap-4">
            <span className="text-5xl">🎉</span>
            <div className="flex-1">
              <h3 className="text-2xl font-bold text-purple-800 mb-2">
                Welcome to VIP Status!
              </h3>
              <p className="text-purple-700">
                You now enjoy 5% discount on all food and earn free delivery credits every 3 orders!
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Free Delivery Tracker removed from banner — progress now shown in VIP Status card */}

      {/* Top Stats Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* Balance Card */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-700">Balance</h3>
            <span className="text-3xl">💰</span>
          </div>
          <p className="text-3xl font-bold text-primary-600 mb-4">
            {dashboard.balance_formatted}
          </p>
          <form onSubmit={handleDeposit} className="flex gap-2">
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Amount"
              value={depositAmount}
              onChange={(e) => setDepositAmount(e.target.value)}
              className="input-field flex-1 text-sm"
            />
            <button
              type="submit"
              disabled={depositing}
              className="btn-primary text-sm px-4"
            >
              {depositing ? '...' : 'Deposit'}
            </button>
          </form>
          <Link to="/customer/transactions" className="text-sm text-primary-600 hover:underline mt-2 block">
            View transactions →
          </Link>
        </div>

        {/* VIP Status Card */}
        <div className={`rounded-xl shadow-md p-6 ${isVIP ? 'bg-gradient-to-br from-yellow-50 to-amber-100 border-2 border-yellow-400' : 'bg-white'}`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-700">VIP Status</h3>
            <span className="text-3xl">{isVIP ? '👑' : '⭐'}</span>
          </div>
          {isVIP ? (
            <>
              <p className="text-2xl font-bold text-amber-600 mb-2">VIP Member</p>
              <div className="space-y-2 text-sm text-gray-600">
                <p>✅ {vip_status.discount_percent}% discount on orders</p>

                {/* Spark-bar progress for free delivery (compact) */}
                {/* Show spark-bar only when no free delivery credits are available */}
                {freeDeliveryCredits === 0 ? (
                  <div className="mt-3">
                    <p className="text-sm text-gray-700 mb-2">Progress to next free delivery</p>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center space-x-1">
                        {[1, 2, 3].map((slot) => (
                          <div
                            key={slot}
                            aria-hidden
                            className={`w-8 h-2 rounded-full transition-colors duration-200 ${
                              slot <= freeDeliveryProgress ? 'bg-amber-500 shadow-[0_0_8px_rgba(250,204,21,0.25)]' : 'bg-gray-200'
                            }`}
                          />
                        ))}
                      </div>
                      <div className="ml-2 text-sm text-gray-700">
                        <span>{freeDeliveryProgress}/3</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3">
                    <p className="text-sm text-gray-700 mb-1">Free delivery credits available</p>
                    <p className="text-sm font-semibold text-green-700">🎁 {freeDeliveryCredits} free delivery credit{freeDeliveryCredits === 1 ? '' : 's'}</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <p className="text-lg font-medium text-gray-600 mb-2">
                {vip_status.vip_eligible ? '🎯 Almost VIP!' : 'Regular Customer'}
              </p>
              <p className="text-sm text-gray-500 mb-3">{vip_status.vip_reason}</p>
              <div className="text-sm text-gray-600 space-y-1">
                <p>💵 Spent: {vip_status.total_spent_formatted}</p>
                <p>📦 Orders: {vip_status.completed_orders}</p>
              </div>
              {/* Progress to VIP */}
              <div className="mt-4">
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>Progress to VIP</span>
                  <span>{Math.min(100, Math.round((vip_status.completed_orders / 3) * 100))}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-amber-400 to-yellow-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, (vip_status.completed_orders / 3) * 100)}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {3 - vip_status.completed_orders} more orders to VIP status!
                </p>
              </div>
            </>
          )}
        </div>

        {/* Quick Stats Card */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-gray-700">Quick Stats</h3>
              {/* Warning badge: green when 0, yellow when some warnings, red when at/above threshold */}
              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                userWarnings === 0 ? 'bg-green-100 text-green-700' :
                (userWarnings >= warningThreshold ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700')
              }`}>{userWarnings === 0 ? 'No warnings' : `${userWarnings} warning${userWarnings === 1 ? '' : 's'}`}</span>
            </div>
            <span className="text-3xl">📊</span>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Account Type</span>
              <span className="font-medium capitalize flex items-center gap-1">
                {isVIP && <span>👑</span>}
                {dashboard.account_type}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total Orders</span>
              <span className="font-medium">{vip_status.completed_orders}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total Spent</span>
              <span className="font-medium">{vip_status.total_spent_formatted}</span>
            </div>
          </div>
          <Link to="/customer/orders" className="text-sm text-primary-600 hover:underline mt-4 block">
            View order history →
          </Link>
        </div>
      </div>

      {/* Featured Section */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* Most Popular Dish */}
        {dashboard.most_popular_dish && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
              🔥 Most Popular Dish
            </h3>
            <Link to={`/dishes/${dashboard.most_popular_dish.id}`} className="block">
              {dashboard.most_popular_dish.picture ? (
                <img
                  src={getBackendImage(dashboard.most_popular_dish.picture)}
                  alt={dashboard.most_popular_dish.name}
                  className="w-full h-32 object-cover rounded-lg mb-3"
                />
              ) : (
                <div className="w-full h-32 bg-gray-200 rounded-lg flex items-center justify-center text-4xl mb-3">
                  🍽️
                </div>
              )}
              <p className="font-semibold text-gray-900 hover:text-primary-600">
                {dashboard.most_popular_dish.name}
              </p>
              <p className="text-primary-600 font-bold">
                {dashboard.most_popular_dish.cost_formatted}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <RatingStars rating={dashboard.most_popular_dish.average_rating} />
                <span className="text-sm text-gray-500">
                  ({dashboard.most_popular_dish.reviews} reviews)
                </span>
              </div>
            </Link>
          </div>
        )}

        {/* Highest Rated Dish */}
        {dashboard.highest_rated_dish && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
              ⭐ Highest Rated Dish
            </h3>
            <Link to={`/dishes/${dashboard.highest_rated_dish.id}`} className="block">
              {dashboard.highest_rated_dish.picture ? (
                <img
                  src={getBackendImage(dashboard.highest_rated_dish.picture)}
                  alt={dashboard.highest_rated_dish.name}
                  className="w-full h-32 object-cover rounded-lg mb-3"
                />
              ) : (
                <div className="w-full h-32 bg-gray-200 rounded-lg flex items-center justify-center text-4xl mb-3">
                  🍽️
                </div>
              )}
              <p className="font-semibold text-gray-900 hover:text-primary-600">
                {dashboard.highest_rated_dish.name}
              </p>
              <p className="text-primary-600 font-bold">
                {dashboard.highest_rated_dish.cost_formatted}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <RatingStars rating={dashboard.highest_rated_dish.average_rating} />
                <span className="text-sm text-gray-500">
                  ({dashboard.highest_rated_dish.reviews} reviews)
                </span>
              </div>
            </Link>
          </div>
        )}

        {/* Top Rated Chef */}
        {dashboard.top_rated_chef && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
              👨‍🍳 Top Rated Chef
            </h3>
            <Link to={`/profiles/chefs/${dashboard.top_rated_chef.id}`} className="block">
              <img
                src={dashboard.top_rated_chef.profile_picture || '/images/chef-placeholder.svg'}
                alt={dashboard.top_rated_chef.display_name || 'Chef'}
                className="w-24 h-24 object-cover rounded-full mx-auto mb-3"
              />
              <p className="font-semibold text-gray-900 text-center hover:text-primary-600">
                {dashboard.top_rated_chef.display_name || dashboard.top_rated_chef.email}
              </p>
              {dashboard.top_rated_chef.specialty && (
                <p className="text-sm text-gray-500 text-center">
                  {dashboard.top_rated_chef.specialty}
                </p>
              )}
              <div className="flex items-center justify-center gap-2 mt-2">
                <RatingStars rating={dashboard.top_rated_chef.average_rating} />
                <span className="text-sm text-gray-500">
                  ({dashboard.top_rated_chef.total_reviews} reviews)
                </span>
              </div>
              <p className="text-sm text-gray-500 text-center mt-1">
                {dashboard.top_rated_chef.total_dishes} dishes
              </p>
            </Link>
          </div>
        )}
      </div>

      {/* Recent Orders */}
      {dashboard.recent_orders.length > 0 && (
        <div className="bg-white rounded-xl shadow-md p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-700">Recent Orders</h3>
            <Link to="/customer/orders" className="text-primary-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-gray-600">Order #</th>
                  <th className="text-left py-3 px-4 text-gray-600">Date</th>
                  <th className="text-left py-3 px-4 text-gray-600">Items</th>
                  <th className="text-left py-3 px-4 text-gray-600">Total</th>
                  <th className="text-left py-3 px-4 text-gray-600">Status</th>
                  <th className="text-left py-3 px-4 text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_orders.map((order) => (
                  <tr key={order.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">#{order.id}</td>
                    <td className="py-3 px-4 text-gray-600">
                      {new Date(order.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">{order.items_count} items</td>
                    <td className="py-3 px-4 font-medium">{order.total_formatted}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        order.status === 'delivered' ? 'bg-green-100 text-green-700' :
                        order.status === 'paid' ? 'bg-blue-100 text-blue-700' :
                        order.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        to="/customer/orders"
                        className="text-primary-600 hover:underline text-sm"
                      >
                        View
                      </Link>
                      {order.can_review && (
                        <Link
                          to="/customer/orders"
                          className="text-green-600 hover:underline text-sm ml-3"
                        >
                          Review
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reviews About Me */}
      {reviewsAboutMe && reviewsAboutMe.reviews.length > 0 && (
        <div className="bg-white rounded-xl shadow-md p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-700 flex items-center gap-2">
              📝 Reviews from Delivery Drivers
              {reviewsAboutMe.average_rating && (
                <span className="text-sm font-normal text-gray-500">
                  (Avg: {reviewsAboutMe.average_rating.toFixed(1)} ⭐)
                </span>
              )}
            </h3>
            <span className="text-sm text-gray-500">{reviewsAboutMe.total} review{reviewsAboutMe.total !== 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-4">
            {reviewsAboutMe.reviews.slice(0, 5).map((review) => (
              <div key={review.id} className="border-b border-gray-100 pb-4 last:border-0">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <RatingStars rating={review.rating} />
                    <span className="text-sm text-gray-600">Order #{review.order_id}</span>
                  </div>
                  <span className="text-sm text-gray-400">
                    {review.created_at ? new Date(review.created_at).toLocaleDateString() : ''}
                  </span>
                </div>
                {review.review_text && (
                  <p className="text-gray-700 mb-2">{review.review_text}</p>
                )}
                <div className="flex gap-4 text-sm">
                  {review.was_polite !== null && (
                    <span className={review.was_polite ? 'text-green-600' : 'text-red-600'}>
                      {review.was_polite ? '✓ Polite' : '✗ Not polite'}
                    </span>
                  )}
                  {review.easy_to_find !== null && (
                    <span className={review.easy_to_find ? 'text-green-600' : 'text-red-600'}>
                      {review.easy_to_find ? '✓ Easy to find' : '✗ Hard to find'}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Favorite Dishes */}
      {dashboard.favorite_dishes.length > 0 && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-xl font-semibold text-gray-700 mb-4">Your Favorites</h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
{dashboard.favorite_dishes.map((dish) => (
  <DishCard
    key={dish.id}
    dish={{
      ...dish,
      picture: dish.picture
        ? `http://localhost:8000/${encodeURI(dish.picture.replace(/^\/+/, ''))}`
        : ''
    }}
  />
))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mt-8 grid sm:grid-cols-4 gap-4">
        <Link
          to="/dishes"
          className="bg-primary-600 text-white rounded-lg p-4 text-center hover:bg-primary-700 transition"
        >
          📖 Browse Menu
        </Link>
        <Link
          to="/cart"
          className="bg-green-600 text-white rounded-lg p-4 text-center hover:bg-green-700 transition"
        >
          🛒 View Cart
        </Link>
        <Link
          to="/forum"
          className="bg-purple-600 text-white rounded-lg p-4 text-center hover:bg-purple-700 transition"
        >
          💬 Forum
        </Link>
        <Link
          to="/chat"
          className="bg-blue-600 text-white rounded-lg p-4 text-center hover:bg-blue-700 transition"
        >
          🤖 Support
        </Link>
      </div>

      {/* Account Management Section */}
      {user?.customer_tier === 'registered' && (
        <div className="mt-8 bg-gray-50 border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">Account Management</h3>
          <p className="text-gray-600 mb-4">Want to close your account?</p>
          <button
            onClick={handleDeregister}
            disabled={deregisterInProgress}
            className="btn-danger"
          >
            {deregisterInProgress ? 'Submitting...' : 'Request Account Closure'}
          </button>
          <p className="text-sm text-gray-500 mt-2">
            Your deregistration request will be sent to the manager for approval.
          </p>
        </div>
      )}
    </div>
  );
}