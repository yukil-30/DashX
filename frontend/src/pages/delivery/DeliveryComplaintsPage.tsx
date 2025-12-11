import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { ComplaintsList, WarningsBanner, RatingStars } from '../../components';
import apiClient from '../../lib/api-client';

interface CustomerReview {
  id: number;
  order_id: number;
  customer_id: number;
  customer_email: string | null;
  reviewer_id: number;
  rating: number;
  review_text: string | null;
  was_polite: boolean | null;
  easy_to_find: boolean | null;
  created_at: string | null;
}

export default function DeliveryComplaintsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'filed' | 'against' | 'customer-reviews'>('against');
  const [showWarning, setShowWarning] = useState(true);
  const [customerReviews, setCustomerReviews] = useState<CustomerReview[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);

  const warnings = user?.warnings || 0;
  const isNearThreshold = warnings >= 2;

  useEffect(() => {
    if (activeTab === 'customer-reviews') {
      fetchCustomerReviews();
    }
  }, [activeTab]);

  const fetchCustomerReviews = async () => {
    setReviewsLoading(true);
    try {
      const response = await apiClient.get('/reviews/my-reviews');
      setCustomerReviews(response.data.customer_reviews || []);
    } catch (err) {
      console.error('Failed to load customer reviews', err);
    } finally {
      setReviewsLoading(false);
    }
  };

  const getWarningMessage = () => {
    if (warnings >= 2) {
      return `You have ${warnings} warnings. This may affect your employment status.`;
    }
    return null;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Warnings Banner */}
      {showWarning && warnings > 0 && (
        <WarningsBanner
          warningsCount={warnings}
          message={getWarningMessage()}
          isNearThreshold={isNearThreshold}
          onDismiss={() => setShowWarning(false)}
        />
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-2">
          <Link to="/delivery/dashboard" className="text-primary-600 hover:text-primary-700">
            ← Back to Dashboard
          </Link>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Complaints & Compliments</h1>
        <p className="text-gray-600 mt-2">
          View complaints filed against you and file feedback about customers.
          You can file complaints about customers from your delivery history.
        </p>
      </div>

      {/* Warning Stats */}
      <div className="bg-white rounded-xl shadow-md p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Status</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Role</p>
            <p className="text-xl font-bold">Delivery Person</p>
          </div>
          <div className={`rounded-lg p-4 ${warnings > 0 ? 'bg-yellow-50' : 'bg-green-50'}`}>
            <p className="text-sm text-gray-600">Warnings</p>
            <p className={`text-xl font-bold ${warnings > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
              {warnings}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Status</p>
            <p className={`text-xl font-bold ${warnings === 0 ? 'text-green-600' : 'text-yellow-600'}`}>
              {warnings === 0 ? 'Good Standing' : 'Under Review'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('against')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'against'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Against You
          </button>
          <button
            onClick={() => setActiveTab('filed')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'filed'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Complaints Filed
          </button>
          <button
            onClick={() => setActiveTab('customer-reviews')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'customer-reviews'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Customer Reviews
          </button>
        </nav>
      </div>

      {/* Content based on tab */}
      {activeTab === 'customer-reviews' ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Customer Reviews You Filed
            </h3>
            <span className="text-sm text-gray-600">Total: {customerReviews.length}</span>
          </div>

          {reviewsLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : customerReviews.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              You haven't reviewed any customers yet. You can review customers from your delivery history.
            </div>
          ) : (
            <div className="space-y-4">
              {customerReviews.map((review) => (
                <div
                  key={review.id}
                  className="bg-white rounded-lg shadow-md p-4 border-l-4 border-blue-400"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <RatingStars rating={review.rating} />
                      <span className="text-sm font-medium">{review.rating}/5</span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {review.created_at ? new Date(review.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>

                  <div className="text-sm text-gray-600 mb-2">
                    <p>Customer: <span className="font-medium">{review.customer_email || `ID: ${review.customer_id}`}</span></p>
                    <p>Order: #{review.order_id}</p>
                  </div>

                  {review.review_text && (
                    <p className="text-gray-800 mb-3">{review.review_text}</p>
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
          )}
        </div>
      ) : (
        <ComplaintsList mode={activeTab} showDispute={activeTab === 'against'} />
      )}

      {/* Help Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">How it Works</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Customers can file complaints about their delivery experience</li>
          <li>• You can dispute complaints if you believe they are unfair</li>
          <li>• Disputed complaints are reviewed by managers</li>
          <li>• You can file complaints about problematic customers from your delivery history</li>
          <li>• Multiple warnings may result in demotion or termination</li>
        </ul>
      </div>
    </div>
  );
}
