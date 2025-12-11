import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../../lib/api-client';
import ReviewCustomerModal from '../../components/ReviewCustomerModal';

interface DeliveryHistoryItem {
  order_id: number;
  customer_id: number;
  customer_email: string;
  delivery_address: string;
  total_cents: number;
  delivery_fee_cents: number;
  ordered_at: string;
  delivered_at: string | null;
  items: Array<{
    dish_id: number;
    dish_name: string;
    quantity: number;
  }>;
  items_count: number;
  rating: number | null;
  review_text: string | null;
  on_time: boolean | null;
  has_review: boolean;
  has_reviewed_customer: boolean;
  can_review_customer: boolean;
}

interface DeliveryStats {
  account_id: number;
  email: string;
  average_rating: number;
  total_reviews: number;
  total_deliveries: number;
  on_time_deliveries: number;
  on_time_percentage: number;
  avg_delivery_minutes: number;
  warnings: number;
  recent_reviews: Array<{
    order_id: number;
    rating: number;
    review_text: string | null;
    on_time: boolean | null;
    created_at: string;
  }>;
}

export default function DeliveryHistoryPage() {
  const [deliveries, setDeliveries] = useState<DeliveryHistoryItem[]>([]);
  const [stats, setStats] = useState<DeliveryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Customer review modal state
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<{
    orderId: number;
    customerId: number;
    customerEmail: string;
  } | null>(null);

  useEffect(() => {
    fetchData();
  }, [page]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [historyRes, statsRes] = await Promise.all([
        apiClient.get(`/delivery/history?page=${page}&per_page=10`),
        apiClient.get('/delivery/stats')
      ]);
      
      setDeliveries(historyRes.data.deliveries || []);
      setTotalPages(historyRes.data.total_pages || 1);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to fetch delivery history:', err);
      toast.error('Failed to load delivery history');
    } finally {
      setLoading(false);
    }
  };

  const handleReviewCustomerClick = (orderId: number, customerId: number, customerEmail: string) => {
    setSelectedCustomer({ orderId, customerId, customerEmail });
    setReviewModalOpen(true);
  };

  const handleReviewSubmitted = () => {
    fetchData();
  };

  const formatCents = (cents: number) => `$${(cents / 100).toFixed(2)}`;
  
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderStars = (rating: number | null) => {
    if (rating === null) return <span className="text-gray-400">No rating yet</span>;
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <span key={star} className={star <= rating ? 'text-yellow-400' : 'text-gray-300'}>
            ★
          </span>
        ))}
        <span className="ml-1 text-sm text-gray-600">({rating}/5)</span>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Delivery History</h1>
        <Link 
          to="/delivery/dashboard" 
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          ← Back to Dashboard
        </Link>
      </div>

      {/* Aggregate Stats */}
      {stats && (
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 rounded-lg shadow-lg p-6 mb-8 text-white">
          <h2 className="text-2xl font-bold mb-4">Your Performance</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <div className="text-4xl font-bold">{stats.average_rating.toFixed(1)}</div>
              <div className="text-sm opacity-90">Average Rating</div>
              <div className="flex mt-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <span 
                    key={star} 
                    className={star <= Math.round(stats.average_rating) ? 'text-yellow-300' : 'text-white/30'}
                  >
                    ★
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div className="text-4xl font-bold">{stats.total_deliveries}</div>
              <div className="text-sm opacity-90">Total Deliveries</div>
              <div className="text-sm mt-1">{stats.total_reviews} reviews</div>
            </div>
            <div>
              <div className="text-4xl font-bold">{stats.on_time_percentage}%</div>
              <div className="text-sm opacity-90">On-Time Rate</div>
              <div className="text-sm mt-1">{stats.on_time_deliveries} of {stats.total_deliveries}</div>
            </div>
            <div>
              <div className="text-4xl font-bold">{stats.avg_delivery_minutes}</div>
              <div className="text-sm opacity-90">Avg. Minutes</div>
              <div className="text-sm mt-1">Delivery time</div>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <>
          {/* Delivery History List */}
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Past Deliveries</h2>
            </div>
            
            {deliveries.length === 0 ? (
              <div className="p-8 text-center text-gray-600">
                <p>No delivery history yet.</p>
                <Link to="/delivery/dashboard" className="text-primary-600 hover:underline mt-2 block">
                  Start delivering to build your history
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {deliveries.map((delivery) => (
                  <div key={delivery.order_id} className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-semibold">Order #{delivery.order_id}</h3>
                        <p className="text-sm text-gray-500">
                          Delivered: {formatDate(delivery.delivered_at)}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-green-600">
                          {formatCents(delivery.delivery_fee_cents)}
                        </div>
                        <p className="text-sm text-gray-500">Delivery fee earned</p>
                      </div>
                    </div>
                    
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <p className="text-sm text-gray-600">
                          <strong>Customer:</strong> {delivery.customer_email}
                        </p>
                        <p className="text-sm text-gray-600">
                          <strong>Delivered to:</strong> {delivery.delivery_address}
                        </p>
                        <p className="text-sm text-gray-600">
                          <strong>Order total:</strong> {formatCents(delivery.total_cents)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm mb-1"><strong>Customer Rating:</strong></p>
                        {renderStars(delivery.rating)}
                        {delivery.on_time !== null && (
                          <p className="text-sm mt-1">
                            {delivery.on_time ? (
                              <span className="text-green-600">✓ Delivered on time</span>
                            ) : (
                              <span className="text-red-600">✗ Late delivery</span>
                            )}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    {delivery.review_text && (
                      <div className="bg-gray-50 rounded-lg p-3 mb-4">
                        <p className="text-sm text-gray-700 italic">"{delivery.review_text}"</p>
                      </div>
                    )}
                    
                    <div className="flex flex-wrap gap-2 mb-4">
                      {delivery.items.map((item, idx) => (
                        <span key={idx} className="bg-gray-100 px-2 py-1 rounded text-sm">
                          {item.quantity}x {item.dish_name}
                        </span>
                      ))}
                    </div>
                    
                    {/* Review Customer Section */}
                    <div className="border-t pt-4 mt-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">Your Review of Customer:</span>
                        {delivery.has_reviewed_customer ? (
                          <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
                            ✓ Reviewed
                          </span>
                        ) : delivery.can_review_customer ? (
                          <button
                            onClick={() => handleReviewCustomerClick(
                              delivery.order_id,
                              delivery.customer_id,
                              delivery.customer_email
                            )}
                            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium"
                          >
                            ⭐ Review Customer
                          </button>
                        ) : (
                          <span className="text-sm text-gray-400">
                            Review available after delivery
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center mt-6 gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="px-4 py-2">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}

          {/* Recent Reviews Section */}
          {stats && stats.recent_reviews && stats.recent_reviews.length > 0 && (
            <div className="mt-8 bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Recent Reviews</h2>
              <div className="space-y-4">
                {stats.recent_reviews.map((review, idx) => (
                  <div key={idx} className="border-b border-gray-100 pb-4 last:border-0">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium">Order #{review.order_id}</p>
                        {renderStars(review.rating)}
                      </div>
                      <span className="text-sm text-gray-500">
                        {formatDate(review.created_at)}
                      </span>
                    </div>
                    {review.review_text && (
                      <p className="text-gray-600 mt-2 italic">"{review.review_text}"</p>
                    )}
                    {review.on_time !== null && (
                      <p className="text-sm mt-1">
                        {review.on_time ? (
                          <span className="text-green-600">✓ On time</span>
                        ) : (
                          <span className="text-red-600">✗ Late</span>
                        )}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Customer Review Modal */}
      {selectedCustomer && (
        <ReviewCustomerModal
          isOpen={reviewModalOpen}
          onClose={() => {
            setReviewModalOpen(false);
            setSelectedCustomer(null);
          }}
          orderId={selectedCustomer.orderId}
          customerId={selectedCustomer.customerId}
          customerEmail={selectedCustomer.customerEmail}
          onReviewSubmitted={handleReviewSubmitted}
        />
      )}
    </div>
  );
}
