import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import apiClient from '../../lib/api-client';
import ReviewDishModal from '../../components/ReviewDishModal';
import { Star, Package, Truck, CheckCircle, Clock } from 'lucide-react';

interface OrderItem {
  dish_id: number;
  dish_name: string;
  dish_picture: string | null;
  quantity: number;
  unit_price_cents: number;
  can_review: boolean;
  has_reviewed: boolean;
}

interface OrderHistory {
  id: number;
  status: string;
  created_at: string;
  delivered_at: string | null;
  subtotal_cents: number;
  delivery_fee_cents: number;
  discount_cents: number;
  total_cents: number;
  total_formatted: string;
  delivery_address: string;
  note: string | null;
  items: OrderItem[];
  delivery_person_id: number | null;
  delivery_person_email: string | null;
  can_review_delivery: boolean;
  has_reviewed_delivery: boolean;
  free_delivery_used: boolean;
  vip_discount_applied: boolean;
}

interface OrderHistoryResponse {
  orders: OrderHistory[];
  total: number;
  page: number;
  per_page: number;
}

export default function OrderHistoryPage() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<OrderHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Review modal state
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedDish, setSelectedDish] = useState<{
    dishId: number;
    dishName: string;
    orderId: number;
  } | null>(null);

  useEffect(() => {
    fetchOrders();
  }, [page, statusFilter]);

  const fetchOrders = async () => {
    setLoading(true);
    setError('');

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '10',
      });
      
      if (statusFilter) {
        params.append('status_filter', statusFilter);
      }

      const response = await apiClient.get<OrderHistoryResponse>(
        `/orders/history/me?${params}`
      );
      
      setOrders(response.data.orders);
      setTotal(response.data.total);
    } catch (err: any) {
      setError('Failed to load order history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReviewClick = (dishId: number, dishName: string, orderId: number) => {
    setSelectedDish({ dishId, dishName, orderId });
    setReviewModalOpen(true);
  };

  const handleReviewSubmitted = () => {
    // Refresh orders to update review status
    fetchOrders();
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      paid: 'bg-blue-100 text-blue-800',
      assigned: 'bg-purple-100 text-purple-800',
      in_transit: 'bg-yellow-100 text-yellow-800',
      delivered: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
    };

    const icons = {
      paid: Package,
      assigned: Truck,
      in_transit: Truck,
      delivered: CheckCircle,
      cancelled: Package,
    };

    const Icon = icons[status as keyof typeof icons] || Package;

    return (
      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${styles[status as keyof typeof styles] || 'bg-gray-100 text-gray-800'}`}>
        <Icon size={14} />
        {status.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  if (!user) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">Please log in to view your order history</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">My Orders</h1>
        
        {/* Filter */}
        <div className="flex gap-4 items-center">
          <label htmlFor="statusFilter" className="text-gray-700 font-medium">
            Filter by status:
          </label>
          <select
            id="statusFilter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="">All Orders</option>
            <option value="paid">Paid</option>
            <option value="assigned">Assigned</option>
            <option value="in_transit">In Transit</option>
            <option value="delivered">Delivered</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 mb-6">
          {error}
        </div>
      )}

      {/* Orders List */}
      {!loading && !error && orders.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-xl">
          <Package size={64} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 text-xl">No orders found</p>
          <p className="text-gray-500 mt-2">
            {statusFilter ? 'Try changing the filter' : 'Start ordering to see your history here'}
          </p>
        </div>
      )}

      {/* Debug: Show what data we're receiving */}
      {!loading && !error && orders.length > 0 && (
        <div className="mb-4 p-4 bg-blue-50 rounded-lg text-xs">
          <details>
            <summary className="cursor-pointer font-semibold">Debug: View Raw Order Data</summary>
            <pre className="mt-2 overflow-auto">{JSON.stringify(orders[0], null, 2)}</pre>
          </details>
        </div>
      )}

      {!loading && !error && orders.length > 0 && (
        <div className="space-y-6">
          {orders.map((order) => (
            <div key={order.id} className="bg-white rounded-xl shadow-md overflow-hidden">
              {/* Order Header */}
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Order #{order.id}
                    </h3>
                    <p className="text-sm text-gray-600">
                      Placed on {new Date(order.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    {getStatusBadge(order.status)}
                    <div className="text-right">
                      <p className="text-sm text-gray-600">Total</p>
                      <p className="text-xl font-bold text-primary-600">
                        {order.total_formatted}
                      </p>
                    </div>
                  </div>
                </div>

                {/* VIP Badges */}
                {(order.vip_discount_applied || order.free_delivery_used) && (
                  <div className="flex gap-2 mt-3">
                    {order.vip_discount_applied && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                        👑 VIP Discount Applied
                      </span>
                    )}
                    {order.free_delivery_used && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ✓ Free Delivery Used
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Order Items */}
              <div className="p-6">
                <h4 className="font-semibold text-gray-900 mb-4">Items</h4>
                <div className="space-y-4">
                  {order.items.map((item) => (
                    <div
                      key={item.dish_id}
                      className="flex items-center gap-4 pb-4 border-b border-gray-100 last:border-0"
                    >
                      {/* Dish Image */}
                      <div className="w-20 h-20 flex-shrink-0">
                        {item.dish_picture ? (
                          <img
                            src={item.dish_picture}
                            alt={item.dish_name}
                            className="w-full h-full object-cover rounded-lg"
                          />
                        ) : (
                          <div className="w-full h-full bg-gray-200 rounded-lg flex items-center justify-center text-2xl">
                            🍽️
                          </div>
                        )}
                      </div>

                      {/* Dish Info */}
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">{item.dish_name}</p>
                        <p className="text-sm text-gray-600">
                          Quantity: {item.quantity} × ${(item.unit_price_cents / 100).toFixed(2)}
                        </p>
                      </div>

                      {/* Review Button */}
                      <div className="flex items-center gap-2">
                        {item.has_reviewed ? (
                          <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
                            <CheckCircle size={16} />
                            Reviewed
                          </span>
                        ) : (
                          // TEMPORARY: Allow reviews on 'paid' status for testing
                          // TODO: Change back to only allow reviews when order.status === 'delivered'
                          // Original condition: item.can_review
                          (order.status === 'paid' || order.status === 'delivered') && !item.has_reviewed ? (
                            <button
                              onClick={() => handleReviewClick(item.dish_id, item.dish_name, order.id)}
                              className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
                            >
                              <Star size={16} />
                              Review
                            </button>
                          ) : (
                            <span className="text-sm text-gray-400 flex items-center gap-1">
                              <Clock size={14} />
                              {order.status === 'delivered' ? 'Already reviewed' : 'Complete order to review'}
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Order Summary */}
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between text-gray-600">
                      <span>Subtotal</span>
                      <span>${(order.subtotal_cents / 100).toFixed(2)}</span>
                    </div>
                    {order.discount_cents > 0 && (
                      <div className="flex justify-between text-green-600">
                        <span>VIP Discount</span>
                        <span>-${(order.discount_cents / 100).toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-gray-600">
                      <span>Delivery Fee</span>
                      <span>
                        {order.free_delivery_used ? (
                          <span className="text-green-600">FREE</span>
                        ) : (
                          `$${(order.delivery_fee_cents / 100).toFixed(2)}`
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between font-semibold text-gray-900 pt-2 border-t border-gray-200">
                      <span>Total</span>
                      <span>{order.total_formatted}</span>
                    </div>
                  </div>
                </div>

                {/* Delivery Address */}
                {order.delivery_address && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm font-medium text-gray-700">Delivery Address</p>
                    <p className="text-sm text-gray-600 mt-1">{order.delivery_address}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 10 && (
        <div className="mt-8 flex justify-center gap-2">
          <button
            onClick={() => setPage(page - 1)}
            disabled={page === 1}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-700">
            Page {page} of {Math.ceil(total / 10)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= Math.ceil(total / 10)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}

      {/* Review Modal */}
      {selectedDish && (
        <ReviewDishModal
          isOpen={reviewModalOpen}
          onClose={() => {
            setReviewModalOpen(false);
            setSelectedDish(null);
          }}
          dishId={selectedDish.dishId}
          dishName={selectedDish.dishName}
          orderId={selectedDish.orderId}
          onReviewSubmitted={handleReviewSubmitted}
        />
      )}
    </div>
  );
}