import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import {
  Order,
  BidListResponse,
  BidWithStats,
  AssignDeliveryRequest,
  formatCents,
} from '../../types/order';
import './ManagerOrderDetail.css';

export function ManagerOrderDetail() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  
  const [order, setOrder] = useState<Order | null>(null);
  const [bidsData, setBidsData] = useState<BidListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [selectedBid, setSelectedBid] = useState<BidWithStats | null>(null);
  const [memo, setMemo] = useState('');
  const [showMemoModal, setShowMemoModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, [orderId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [orderRes, bidsRes] = await Promise.all([
        apiClient.get<Order>(`/orders/${orderId}`),
        apiClient.get<BidListResponse>(`/orders/${orderId}/bids`),
      ]);
      setOrder(orderRes.data);
      setBidsData(bidsRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load order data');
    } finally {
      setLoading(false);
    }
  };

  const handleAssignClick = (bid: BidWithStats) => {
    setSelectedBid(bid);
    if (!bid.is_lowest) {
      // Non-lowest bid requires memo
      setShowMemoModal(true);
    } else {
      // Lowest bid - assign directly
      assignDelivery(bid, '');
    }
  };

  const assignDelivery = async (bid: BidWithStats, memoText: string) => {
    setAssigning(true);
    try {
      const request: AssignDeliveryRequest = {
        delivery_id: bid.deliveryPersonID,
      };
      if (memoText.trim()) {
        request.memo = memoText.trim();
      }
      
      await apiClient.post(
        `/orders/${orderId}/assign`,
        request
      );
      
      setShowMemoModal(false);
      setMemo('');
      setSelectedBid(null);
      
      // Refresh data
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to assign delivery');
    } finally {
      setAssigning(false);
    }
  };

  const handleMemoSubmit = () => {
    if (selectedBid && memo.trim()) {
      assignDelivery(selectedBid, memo);
    }
  };

  const getRatingClass = (rating: number): string => {
    if (rating >= 4.5) return 'rating-excellent';
    if (rating >= 4.0) return 'rating-good';
    if (rating >= 3.0) return 'rating-average';
    return 'rating-poor';
  };

  const getOnTimeClass = (percentage: number): string => {
    if (percentage >= 90) return 'ontime-excellent';
    if (percentage >= 80) return 'ontime-good';
    if (percentage >= 70) return 'ontime-average';
    return 'ontime-poor';
  };

  if (loading) {
    return <div className="loading">Loading order details...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="error">{error}</p>
        <button onClick={fetchData}>Retry</button>
      </div>
    );
  }

  if (!order) {
    return <div className="error">Order not found</div>;
  }

  const isAssignable = order.status === 'paid';

  return (
    <div className="manager-order-detail">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h1>Order #{order.id}</h1>
        <span className={`status-badge status-${order.status}`}>
          {order.status.toUpperCase()}
        </span>
      </header>

      <section className="order-info">
        <h2>Order Details</h2>
        <div className="info-grid">
          <div className="info-item">
            <label>Customer ID</label>
            <span>{order.accountID}</span>
          </div>
          <div className="info-item">
            <label>Date</label>
            <span>{order.dateTime ? new Date(order.dateTime).toLocaleString() : 'N/A'}</span>
          </div>
          <div className="info-item">
            <label>Delivery Address</label>
            <span>{order.delivery_address || 'N/A'}</span>
          </div>
          <div className="info-item">
            <label>Subtotal</label>
            <span>{formatCents(order.subtotal_cents)}</span>
          </div>
          <div className="info-item">
            <label>Delivery Fee</label>
            <span>{formatCents(order.delivery_fee)}</span>
          </div>
          <div className="info-item">
            <label>Final Cost</label>
            <span className="final-cost">{formatCents(order.finalCost)}</span>
          </div>
        </div>

        {order.ordered_dishes.length > 0 && (
          <div className="dishes-list">
            <h3>Items</h3>
            <ul>
              {order.ordered_dishes.map((dish) => (
                <li key={dish.DishID}>
                  {dish.quantity}x {dish.dish_name || `Dish #${dish.DishID}`}
                  {dish.dish_cost && ` - ${formatCents(dish.dish_cost * dish.quantity)}`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="bids-section">
        <h2>Delivery Bids ({bidsData?.bids.length || 0})</h2>
        
        {!isAssignable && (
          <div className="info-banner">
            Order is already {order.status}. Cannot reassign delivery.
          </div>
        )}

        {bidsData?.bids.length === 0 ? (
          <p className="no-bids">No bids yet. Waiting for delivery personnel to bid.</p>
        ) : (
          <div className="bids-table-container">
            <table className="bids-table">
              <thead>
                <tr>
                  <th>Delivery Person</th>
                  <th>Bid Amount</th>
                  <th>Est. Time</th>
                  <th>Rating</th>
                  <th>On-Time %</th>
                  <th>Deliveries</th>
                  <th>Warnings</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {bidsData?.bids.map((bid) => (
                  <tr
                    key={bid.id}
                    className={`bid-row ${bid.is_lowest ? 'lowest-bid' : ''}`}
                  >
                    <td>
                      <span className="delivery-email">{bid.delivery_person.email}</span>
                      {bid.is_lowest && <span className="lowest-badge">LOWEST</span>}
                    </td>
                    <td className="bid-amount">{formatCents(bid.bidAmount)}</td>
                    <td>{bid.estimated_minutes} min</td>
                    <td>
                      <span className={`rating ${getRatingClass(bid.delivery_person.average_rating)}`}>
                        ⭐ {bid.delivery_person.average_rating.toFixed(1)}
                      </span>
                      <span className="review-count">({bid.delivery_person.reviews} reviews)</span>
                    </td>
                    <td>
                      <span className={`ontime ${getOnTimeClass(bid.delivery_person.on_time_percentage)}`}>
                        {bid.delivery_person.on_time_percentage.toFixed(0)}%
                      </span>
                    </td>
                    <td>{bid.delivery_person.total_deliveries}</td>
                    <td>
                      {bid.delivery_person.warnings > 0 ? (
                        <span className="warnings">⚠️ {bid.delivery_person.warnings}</span>
                      ) : (
                        <span className="no-warnings">✓</span>
                      )}
                    </td>
                    <td>
                      <button
                        className={`assign-btn ${bid.is_lowest ? 'assign-lowest' : 'assign-other'}`}
                        onClick={() => handleAssignClick(bid)}
                        disabled={!isAssignable || assigning}
                      >
                        {assigning && selectedBid?.id === bid.id ? 'Assigning...' : 'Assign'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Memo Modal for non-lowest bid */}
      {showMemoModal && selectedBid && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Justification Required</h3>
            <p>
              You are assigning a non-lowest bid ({formatCents(selectedBid.bidAmount)}).
              The lowest bid is {formatCents(bidsData?.bids.find(b => b.is_lowest)?.bidAmount || 0)}.
            </p>
            <p>Please provide a justification for this decision:</p>
            <textarea
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="e.g., Better on-time record, higher rating, etc."
              rows={4}
            />
            <div className="modal-actions">
              <button
                className="cancel-btn"
                onClick={() => {
                  setShowMemoModal(false);
                  setSelectedBid(null);
                  setMemo('');
                }}
              >
                Cancel
              </button>
              <button
                className="confirm-btn"
                onClick={handleMemoSubmit}
                disabled={!memo.trim() || assigning}
              >
                {assigning ? 'Assigning...' : 'Confirm Assignment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ManagerOrderDetail;
