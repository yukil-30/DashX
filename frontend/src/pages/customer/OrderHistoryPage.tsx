import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../../lib/api-client';
import { OrderHistory, OrderHistoryListResponse } from '../../types/api';
import { RatingStars } from '../../components';

export default function OrderHistoryPage() {
  const [orders, setOrders] = useState<OrderHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState<OrderHistory | null>(null);
  const [reviewModal, setReviewModal] = useState<{
    type: 'dish' | 'delivery';
    orderId: number;
    dishId?: number;
    dishName?: string;
  } | null>(null);
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState('');
  const [onTime, setOnTime] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchOrders();
  }, [page]);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<OrderHistoryListResponse>(
        `/orders/history/me?page=${page}&per_page=10`
      );
      setOrders(response.data.orders);
      setTotal(response.data.total);
    } catch (err: any) {
      toast.error('Failed to load order history');
    } finally {
      setLoading(false);
    }
  };

  const submitDishReview = async () => {
    if (!reviewModal || reviewModal.type !== 'dish') return;
    setSubmitting(true);
    try {
      await apiClient.post('/reviews/dish', {
        dish_id: reviewModal.dishId,
        order_id: reviewModal.orderId,
        rating,
        review_text: reviewText || null,
      });
      toast.success('Review submitted!');
      setReviewModal(null);
      setRating(5);
      setReviewText('');
      fetchOrders();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const submitDeliveryReview = async () => {
    if (!reviewModal || reviewModal.type !== 'delivery') return;
    setSubmitting(true);
    try {
      await apiClient.post('/reviews/delivery', {
        order_id: reviewModal.orderId,
        rating,
        review_text: reviewText || null,
        on_time: onTime,
      });
      toast.success('Delivery review submitted!');
      setReviewModal(null);
      setRating(5);
      setReviewText('');
      setOnTime(null);
      fetchOrders();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && orders.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Order History</h1>
        <Link to="/dashboard" className="text-primary-600 hover:underline">
          ← Back to Dashboard
        </Link>
      </div>

      {orders.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📦</div>
          <p className="text-gray-600 text-xl mb-6">No orders yet</p>
          <Link to="/dishes" className="btn-primary">
            Browse Menu
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {orders.map((order) => (
            <div
              key={order.id}
              className="bg-white rounded-xl shadow-md overflow-hidden"
            >
              {/* Order Header */}
              <div className="bg-gray-50 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div>
                    <span className="font-semibold text-gray-900">Order #{order.id}</span>
                    <span className="text-gray-500 ml-3">
                      {new Date(order.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    order.status === 'delivered' ? 'bg-green-100 text-green-700' :
                    order.status === 'paid' ? 'bg-blue-100 text-blue-700' :
                    order.status === 'assigned' ? 'bg-purple-100 text-purple-700' :
                    order.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {order.status}
                  </span>
                  {order.vip_discount_applied && (
                    <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                      VIP Discount Applied
                    </span>
                  )}
                  {order.free_delivery_used && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                      Free Delivery
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-primary-600">{order.total_formatted}</p>
                </div>
              </div>

              {/* Order Items */}
              <div className="px-6 py-4">
                <div className="grid gap-4">
                  {order.items.map((item) => (
                    <div key={item.dish_id} className="flex items-center gap-4">
                      {item.dish_picture ? (
                        <img
                          src={item.dish_picture}
                          alt={item.dish_name}
                          className="w-16 h-16 object-cover rounded-lg"
                        />
                      ) : (
                        <div className="w-16 h-16 bg-gray-200 rounded-lg flex items-center justify-center text-2xl">
                          🍽️
                        </div>
                      )}
                      <div className="flex-1">
                        <Link
                          to={`/dishes/${item.dish_id}`}
                          className="font-medium text-gray-900 hover:text-primary-600"
                        >
                          {item.dish_name}
                        </Link>
                        <p className="text-gray-500 text-sm">
                          Qty: {item.quantity} × ${(item.unit_price_cents / 100).toFixed(2)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">
                          ${((item.unit_price_cents * item.quantity) / 100).toFixed(2)}
                        </p>
                        {item.can_review && !item.has_reviewed && (
                          <button
                            onClick={() => setReviewModal({
                              type: 'dish',
                              orderId: order.id,
                              dishId: item.dish_id,
                              dishName: item.dish_name,
                            })}
                            className="text-sm text-green-600 hover:underline"
                          >
                            Leave Review
                          </button>
                        )}
                        {item.has_reviewed && (
                          <span className="text-sm text-gray-500">✓ Reviewed</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Order Footer */}
              <div className="bg-gray-50 px-6 py-4 flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  <p>📍 {order.delivery_address}</p>
                  {order.delivery_person_email && (
                    <p>🚚 Delivered by: {order.delivery_person_email}</p>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right text-sm text-gray-600">
                    <p>Subtotal: ${(order.subtotal_cents / 100).toFixed(2)}</p>
                    {order.discount_cents > 0 && (
                      <p className="text-green-600">Discount: -${(order.discount_cents / 100).toFixed(2)}</p>
                    )}
                    <p>Delivery: ${(order.delivery_fee_cents / 100).toFixed(2)}</p>
                  </div>
                  {order.can_review_delivery && (
                    <button
                      onClick={() => setReviewModal({
                        type: 'delivery',
                        orderId: order.id,
                      })}
                      className="btn-secondary text-sm"
                    >
                      Review Delivery
                    </button>
                  )}
                  {order.has_reviewed_delivery && (
                    <span className="text-sm text-gray-500">✓ Delivery Reviewed</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 10 && (
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary disabled:opacity-50"
          >
            ← Previous
          </button>
          <span className="py-2 px-4">
            Page {page} of {Math.ceil(total / 10)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(total / 10)}
            className="btn-secondary disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      )}

      {/* Review Modal */}
      {reviewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-semibold mb-4">
              {reviewModal.type === 'dish'
                ? `Review: ${reviewModal.dishName}`
                : 'Review Delivery'}
            </h3>

            {/* Rating */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rating
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => setRating(star)}
                    className={`text-3xl ${
                      star <= rating ? 'text-yellow-400' : 'text-gray-300'
                    }`}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>

            {/* On Time (delivery only) */}
            {reviewModal.type === 'delivery' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Was the delivery on time?
                </label>
                <div className="flex gap-4">
                  <button
                    onClick={() => setOnTime(true)}
                    className={`px-4 py-2 rounded-lg ${
                      onTime === true
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    Yes ✓
                  </button>
                  <button
                    onClick={() => setOnTime(false)}
                    className={`px-4 py-2 rounded-lg ${
                      onTime === false
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    No ✗
                  </button>
                </div>
              </div>
            )}

            {/* Review Text */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Review (optional)
              </label>
              <textarea
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                className="input-field resize-none"
                rows={3}
                placeholder="Share your experience..."
              />
            </div>

            {/* Actions */}
            <div className="flex gap-4">
              <button
                onClick={() => setReviewModal(null)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={reviewModal.type === 'dish' ? submitDishReview : submitDeliveryReview}
                disabled={submitting}
                className="btn-primary flex-1"
              >
                {submitting ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
