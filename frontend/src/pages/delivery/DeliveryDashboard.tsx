import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../../lib/api-client';

interface OrderItem {
  dish_id: number;
  dish_name: string;
  quantity: number;
  unit_price_cents: number;
}

interface AvailableOrder {
  id: number;
  customer_email: string;
  delivery_address: string;
  subtotal_cents: number;
  delivery_fee_cents: number;
  total_cents: number;
  created_at: string;
  bidding_closes_at: string | null;
  items: OrderItem[];
  items_count: number;
  bid_count: number;
  lowest_bid_cents: number | null;
  has_user_bid: boolean;
  user_bid_id: number | null;
  user_bid_amount: number | null;
  note: string | null;
}

interface MyBid {
  bid_id: number;
  order_id: number;
  bid_amount_cents: number;
  estimated_minutes: number;
  created_at: string;
  bid_status: string;
  is_lowest: boolean;
  order_status: string;
  order_delivery_address: string;
  order_total_cents: number;
}

interface AssignedOrder {
  id: number;
  customer_email: string;
  delivery_address: string;
  total_cents: number;
  delivery_fee_cents: number;
  estimated_minutes: number;
  status: string;
  created_at: string;
  items: OrderItem[];
  items_count: number;
  note: string | null;
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
  total_bids: number;
  pending_deliveries: number;
}

export default function DeliveryDashboard() {
  const [availableOrders, setAvailableOrders] = useState<AvailableOrder[]>([]);
  const [myBids, setMyBids] = useState<MyBid[]>([]);
  const [assignedOrders, setAssignedOrders] = useState<AssignedOrder[]>([]);
  const [stats, setStats] = useState<DeliveryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'available' | 'bids' | 'assigned'>('available');
  
  // Bid modal state
  const [bidModalOpen, setBidModalOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<AvailableOrder | null>(null);
  const [bidAmount, setBidAmount] = useState('');
  const [estimatedMinutes, setEstimatedMinutes] = useState('30');
  const [bidding, setBidding] = useState(false);
  
  // Mark delivered state
  const [delivering, setDelivering] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [ordersRes, bidsRes, assignedRes, statsRes] = await Promise.all([
        apiClient.get('/delivery/available-orders'),
        apiClient.get('/delivery/my-bids'),
        apiClient.get('/delivery/assigned'),
        apiClient.get('/delivery/stats')
      ]);
      
      setAvailableOrders(ordersRes.data.orders || []);
      setMyBids(bidsRes.data.bids || []);
      setAssignedOrders(assignedRes.data.orders || []);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to fetch delivery data:', err);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const openBidModal = (order: AvailableOrder) => {
    setSelectedOrder(order);
    setBidAmount(order.lowest_bid_cents ? String((order.lowest_bid_cents - 50) / 100) : '5.00');
    setEstimatedMinutes('30');
    setBidModalOpen(true);
  };

  const closeBidModal = () => {
    setBidModalOpen(false);
    setSelectedOrder(null);
    setBidAmount('');
  };

  const submitBid = async () => {
    if (!selectedOrder) return;
    
    const priceCents = Math.round(parseFloat(bidAmount) * 100);
    if (isNaN(priceCents) || priceCents <= 0) {
      toast.error('Please enter a valid bid amount');
      return;
    }
    
    const minutes = parseInt(estimatedMinutes, 10);
    if (isNaN(minutes) || minutes <= 0) {
      toast.error('Please enter valid estimated minutes');
      return;
    }
    
    setBidding(true);
    try {
      await apiClient.post(`/delivery/orders/${selectedOrder.id}/bid`, {
        price_cents: priceCents,
        estimated_minutes: minutes
      });
      toast.success('Bid placed successfully!');
      closeBidModal();
      fetchData();
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to place bid';
      toast.error(detail);
    } finally {
      setBidding(false);
    }
  };

  const markDelivered = async (orderId: number) => {
    setDelivering(orderId);
    try {
      await apiClient.post(`/delivery/orders/${orderId}/mark-delivered`);
      toast.success('Order marked as delivered!');
      fetchData();
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to mark as delivered';
      toast.error(detail);
    } finally {
      setDelivering(null);
    }
  };

  const formatCents = (cents: number) => `$${(cents / 100).toFixed(2)}`;

  const formatTimeRemaining = (closesAt: string | null) => {
    if (!closesAt) return 'Open';
    const closes = new Date(closesAt);
    const now = new Date();
    const diff = closes.getTime() - now.getTime();
    if (diff <= 0) return 'Closed';
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m left`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m left`;
  };

  const getBidStatusColor = (status: string) => {
    switch (status) {
      case 'accepted': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Delivery Dashboard</h1>
        <Link 
          to="/delivery/history" 
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          View History →
        </Link>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <div className="text-3xl font-bold text-primary-600">{stats.total_deliveries}</div>
            <div className="text-sm text-gray-600">Total Deliveries</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <div className="text-3xl font-bold text-yellow-600">
              {stats.average_rating.toFixed(1)} ⭐
            </div>
            <div className="text-sm text-gray-600">Rating ({stats.total_reviews} reviews)</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <div className="text-3xl font-bold text-green-600">{stats.on_time_percentage}%</div>
            <div className="text-sm text-gray-600">On Time</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">{stats.pending_deliveries}</div>
            <div className="text-sm text-gray-600">Pending</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <div className="text-3xl font-bold text-purple-600">{stats.total_bids}</div>
            <div className="text-sm text-gray-600">Total Bids</div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <>
          {/* Tab Navigation */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('available')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'available'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Available Orders ({availableOrders.length})
              </button>
              <button
                onClick={() => setActiveTab('bids')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'bids'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                My Bids ({myBids.length})
              </button>
              <button
                onClick={() => setActiveTab('assigned')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'assigned'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Assigned ({assignedOrders.length})
              </button>
            </nav>
          </div>

          {/* Available Orders Tab */}
          {activeTab === 'available' && (
            <div className="space-y-4">
              {availableOrders.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                  <p className="text-gray-600">No orders available for bidding at the moment.</p>
                </div>
              ) : (
                availableOrders.map(order => (
                  <div key={order.id} className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-semibold">Order #{order.id}</h3>
                        <p className="text-sm text-gray-500">{order.items_count} items • {formatCents(order.total_cents)}</p>
                      </div>
                      <div className="text-right">
                        <span className={`inline-block px-2 py-1 rounded text-sm ${
                          order.bidding_closes_at && new Date(order.bidding_closes_at) < new Date()
                            ? 'bg-red-100 text-red-800'
                            : 'bg-green-100 text-green-800'
                        }`}>
                          {formatTimeRemaining(order.bidding_closes_at)}
                        </span>
                        <p className="text-sm text-gray-500 mt-1">{order.bid_count} bids</p>
                      </div>
                    </div>
                    
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <p className="text-sm text-gray-600">
                          <strong>Delivery to:</strong> {order.delivery_address}
                        </p>
                        {order.note && (
                          <p className="text-sm text-gray-500 mt-1">
                            <strong>Note:</strong> {order.note}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        {order.lowest_bid_cents && (
                          <p className="text-sm">
                            Lowest bid: <strong className="text-green-600">{formatCents(order.lowest_bid_cents)}</strong>
                          </p>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <div className="flex flex-wrap gap-2">
                        {order.items.slice(0, 3).map((item, idx) => (
                          <span key={idx} className="bg-gray-100 px-2 py-1 rounded text-sm">
                            {item.quantity}x {item.dish_name}
                          </span>
                        ))}
                        {order.items.length > 3 && (
                          <span className="bg-gray-100 px-2 py-1 rounded text-sm">
                            +{order.items.length - 3} more
                          </span>
                        )}
                      </div>
                      
                      {order.has_user_bid ? (
                        <span className="text-sm text-gray-600">
                          Your bid: {formatCents(order.user_bid_amount || 0)}
                        </span>
                      ) : (
                        <button
                          onClick={() => openBidModal(order)}
                          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
                        >
                          Place Bid
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* My Bids Tab */}
          {activeTab === 'bids' && (
            <div className="space-y-4">
              {myBids.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                  <p className="text-gray-600">You haven't placed any bids yet.</p>
                </div>
              ) : (
                myBids.map(bid => (
                  <div key={bid.bid_id} className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-lg font-semibold">Order #{bid.order_id}</h3>
                        <p className="text-sm text-gray-500">
                          Your bid: {formatCents(bid.bid_amount_cents)} • {bid.estimated_minutes} min delivery
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          Deliver to: {bid.order_delivery_address}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getBidStatusColor(bid.bid_status)}`}>
                          {bid.bid_status.charAt(0).toUpperCase() + bid.bid_status.slice(1)}
                        </span>
                        {bid.is_lowest && bid.bid_status === 'pending' && (
                          <p className="text-xs text-green-600 mt-1">✓ Lowest bid</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Assigned Orders Tab */}
          {activeTab === 'assigned' && (
            <div className="space-y-4">
              {assignedOrders.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                  <p className="text-gray-600">No orders currently assigned to you.</p>
                </div>
              ) : (
                assignedOrders.map(order => (
                  <div key={order.id} className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-semibold">Order #{order.id}</h3>
                        <p className="text-sm text-gray-500">
                          {order.items_count} items • Delivery fee: {formatCents(order.delivery_fee_cents)}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          <strong>Status:</strong> {order.status}
                        </p>
                      </div>
                      <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                        ETA: {order.estimated_minutes} min
                      </span>
                    </div>
                    
                    <div className="mb-4">
                      <p className="text-sm">
                        <strong>Customer:</strong> {order.customer_email}
                      </p>
                      <p className="text-sm">
                        <strong>Deliver to:</strong> {order.delivery_address}
                      </p>
                      {order.note && (
                        <p className="text-sm text-gray-500">
                          <strong>Note:</strong> {order.note}
                        </p>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap gap-2 mb-4">
                      {order.items.map((item, idx) => (
                        <span key={idx} className="bg-gray-100 px-2 py-1 rounded text-sm">
                          {item.quantity}x {item.dish_name}
                        </span>
                      ))}
                    </div>
                    
                    <button
                      onClick={() => markDelivered(order.id)}
                      disabled={delivering === order.id}
                      className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                    >
                      {delivering === order.id ? 'Marking...' : '✓ Mark as Delivered'}
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      {/* Bid Modal */}
      {bidModalOpen && selectedOrder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Place Bid for Order #{selectedOrder.id}</h2>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                {selectedOrder.items_count} items • Total: {formatCents(selectedOrder.total_cents)}
              </p>
              <p className="text-sm text-gray-600">
                Deliver to: {selectedOrder.delivery_address}
              </p>
              {selectedOrder.lowest_bid_cents && (
                <p className="text-sm text-green-600 mt-2">
                  Current lowest bid: {formatCents(selectedOrder.lowest_bid_cents)}
                </p>
              )}
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Your Bid Amount ($)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={bidAmount}
                onChange={(e) => setBidAmount(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="5.00"
              />
            </div>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Estimated Delivery Time (minutes)
              </label>
              <input
                type="number"
                min="1"
                max="180"
                value={estimatedMinutes}
                onChange={(e) => setEstimatedMinutes(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="30"
              />
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={closeBidModal}
                className="flex-1 bg-gray-200 text-gray-800 py-2 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={submitBid}
                disabled={bidding}
                className="flex-1 bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {bidding ? 'Placing...' : 'Place Bid'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
