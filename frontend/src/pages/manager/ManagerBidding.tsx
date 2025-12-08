import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import './ManagerBidding.css';

interface BiddingOrder {
  order_id: number;
  customer_email: string;
  order_total: number;
  delivery_address: string;
  created_at: string;
  bids_count: number;
  lowest_bid_amount: number | null;
  lowest_bid_delivery_id: number | null;
}

interface BiddingOrderListResponse {
  orders: BiddingOrder[];
  total: number;
}

interface Bid {
  id: number;
  deliveryPersonID: number;
  orderID: number;
  bidAmount: number;
  estimated_minutes: number;
  is_lowest: boolean;
  delivery_person: {
    account_id: number;
    email: string;
    average_rating: number;
    reviews: number;
    total_deliveries: number;
    on_time_deliveries: number;
    on_time_percentage: number;
    avg_delivery_minutes: number;
    warnings: number;
  };
}

interface BidsResponse {
  order_id: number;
  bids: Bid[];
  lowest_bid_id: number | null;
}

interface AssignResult {
  message: string;
  order_id: number;
  bid_id: number;
  delivery_person_id: number;
  delivery_fee: number;
  is_lowest_bid: boolean;
  memo_required: boolean;
  memo_saved: boolean;
}

export function ManagerBidding() {
  const [orders, setOrders] = useState<BiddingOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<BiddingOrder | null>(null);
  const [bids, setBids] = useState<Bid[]>([]);
  const [bidsLoading, setBidsLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [memo, setMemo] = useState('');
  const [assignResult, setAssignResult] = useState<AssignResult | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<BiddingOrderListResponse>('/manager/bidding/orders');
      setOrders(response.data.orders);
      setTotal(response.data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load orders');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const fetchBids = async (orderId: number) => {
    setBidsLoading(true);
    try {
      const response = await apiClient.get<BidsResponse>(`/orders/${orderId}/bids`);
      setBids(response.data.bids);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load bids');
    } finally {
      setBidsLoading(false);
    }
  };

  const handleOrderSelect = (order: BiddingOrder) => {
    setSelectedOrder(order);
    setBids([]);
    setMemo('');
    setAssignResult(null);
    fetchBids(order.order_id);
  };

  const handleAssign = async (bid: Bid) => {
    if (!selectedOrder) return;

    // Check if memo is required
    const lowestBid = bids.find(b => b.is_lowest);
    const isLowest = lowestBid?.id === bid.id;

    if (!isLowest && !memo.trim()) {
      setError('Memo is required when selecting a non-lowest bid');
      return;
    }

    setAssigning(true);
    setError(null);

    try {
      const response = await apiClient.post<AssignResult>(
        `/manager/bidding/orders/${selectedOrder.order_id}/assign`,
        {
          bid_id: bid.id,
          memo: memo.trim() || null
        }
      );

      setAssignResult(response.data);

      // Refresh after showing result
      setTimeout(() => {
        fetchOrders();
        setSelectedOrder(null);
        setBids([]);
        setMemo('');
        setAssignResult(null);
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to assign bid');
    } finally {
      setAssigning(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const getRatingBadge = (rating: number) => {
    if (rating >= 4.5) return <span className="rating-badge excellent">⭐ {rating.toFixed(1)}</span>;
    if (rating >= 4) return <span className="rating-badge good">⭐ {rating.toFixed(1)}</span>;
    if (rating >= 3) return <span className="rating-badge average">⭐ {rating.toFixed(1)}</span>;
    return <span className="rating-badge poor">⚠️ {rating.toFixed(1)}</span>;
  };

  return (
    <div className="manager-bidding">
      <header className="page-header">
        <div className="header-left">
          <Link to="/manager/dashboard" className="back-link">← Dashboard</Link>
          <h1>🚗 Bidding Management</h1>
        </div>
        <div className="header-stats">
          <span className="stat">{total} Orders Awaiting Assignment</span>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="bidding-layout">
        {/* Orders List */}
        <div className="orders-panel">
          <div className="panel-header">
            <h2>📦 Orders with Bids</h2>
            <button onClick={fetchOrders} className="btn-refresh">🔄</button>
          </div>

          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
            </div>
          ) : orders.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">✅</span>
              <p>No orders awaiting assignment</p>
            </div>
          ) : (
            <div className="orders-list">
              {orders.map((order) => (
                <div
                  key={order.order_id}
                  className={`order-card ${selectedOrder?.order_id === order.order_id ? 'selected' : ''}`}
                  onClick={() => handleOrderSelect(order)}
                >
                  <div className="order-header">
                    <span className="order-id">Order #{order.order_id}</span>
                    <span className="order-total">{formatCurrency(order.order_total)}</span>
                  </div>
                  <p className="order-customer">{order.customer_email}</p>
                  <p className="order-address">{order.delivery_address}</p>
                  <div className="order-footer">
                    <span className="bids-count">🏷️ {order.bids_count} bids</span>
                    {order.lowest_bid_amount && (
                      <span className="lowest-bid">
                        Lowest: {formatCurrency(order.lowest_bid_amount)}
                      </span>
                    )}
                  </div>
                  <span className="order-date">{formatDate(order.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bids Panel */}
        <div className="bids-panel">
          {!selectedOrder ? (
            <div className="select-order-prompt">
              <span className="prompt-icon">👈</span>
              <p>Select an order to view bids</p>
            </div>
          ) : (
            <>
              <div className="panel-header">
                <h2>🏷️ Bids for Order #{selectedOrder.order_id}</h2>
              </div>

              <div className="order-summary">
                <p><strong>Customer:</strong> {selectedOrder.customer_email}</p>
                <p><strong>Total:</strong> {formatCurrency(selectedOrder.order_total)}</p>
                <p><strong>Address:</strong> {selectedOrder.delivery_address}</p>
              </div>

              {assignResult ? (
                <div className="assign-result">
                  <span className="result-icon">✅</span>
                  <h3>Bid Assigned!</h3>
                  <p>Delivery fee: {formatCurrency(assignResult.delivery_fee)}</p>
                  {!assignResult.is_lowest_bid && (
                    <p className="memo-note">📝 Memo saved for non-lowest bid selection</p>
                  )}
                </div>
              ) : bidsLoading ? (
                <div className="loading-container">
                  <div className="loading-spinner"></div>
                </div>
              ) : bids.length === 0 ? (
                <div className="empty-state">
                  <p>No bids yet</p>
                </div>
              ) : (
                <>
                  <div className="bids-list">
                    {bids.map((bid) => (
                      <div
                        key={bid.id}
                        className={`bid-card ${bid.is_lowest ? 'lowest' : ''}`}
                      >
                        <div className="bid-header">
                          <div className="bid-amount">
                            {formatCurrency(bid.bidAmount)}
                            {bid.is_lowest && <span className="lowest-badge">Lowest</span>}
                          </div>
                          <span className="bid-time">⏱️ {bid.estimated_minutes} min</span>
                        </div>

                        <div className="delivery-person">
                          <p className="dp-email">{bid.delivery_person.email}</p>
                          <div className="dp-stats">
                            {getRatingBadge(bid.delivery_person.average_rating)}
                            <span className="dp-stat">
                              📦 {bid.delivery_person.total_deliveries} deliveries
                            </span>
                            <span className="dp-stat">
                              ⏰ {bid.delivery_person.on_time_percentage.toFixed(0)}% on-time
                            </span>
                            {bid.delivery_person.warnings > 0 && (
                              <span className="dp-warnings">
                                ⚠️ {bid.delivery_person.warnings} warnings
                              </span>
                            )}
                          </div>
                        </div>

                        <button
                          onClick={() => handleAssign(bid)}
                          className={`assign-btn ${bid.is_lowest ? 'primary' : 'secondary'}`}
                          disabled={assigning}
                        >
                          {assigning ? 'Assigning...' : 'Select This Bid'}
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="memo-section">
                    <label>
                      📝 Assignment Memo
                      <span className="memo-hint">(Required if not selecting lowest bid)</span>
                    </label>
                    <textarea
                      value={memo}
                      onChange={(e) => setMemo(e.target.value)}
                      placeholder="Explain why you chose a higher bid (e.g., better rating, faster delivery time)..."
                      rows={3}
                    />
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ManagerBidding;
