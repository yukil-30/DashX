import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Order, formatCents } from '../../types/order';
import './ManagerOrders.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ManagerOrdersProps {
  token: string;
}

export function ManagerOrders({ token }: ManagerOrdersProps) {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const headers = {
    Authorization: `Bearer ${token}`,
  };

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const fetchOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 50 };
      if (statusFilter) {
        params.status_filter = statusFilter;
      }
      const response = await axios.get<Order[]>(`${API_URL}/orders`, {
        headers,
        params,
      });
      setOrders(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const getStatusClass = (status: string): string => {
    switch (status) {
      case 'paid': return 'status-paid';
      case 'assigned': return 'status-assigned';
      case 'delivered': return 'status-delivered';
      case 'cancelled': return 'status-cancelled';
      default: return 'status-default';
    }
  };

  if (loading) {
    return <div className="loading">Loading orders...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="error">{error}</p>
        <button onClick={fetchOrders}>Retry</button>
      </div>
    );
  }

  const paidOrders = orders.filter(o => o.status === 'paid');
  const otherOrders = orders.filter(o => o.status !== 'paid');

  return (
    <div className="manager-orders">
      <header className="page-header">
        <h1>📋 Order Management</h1>
        <div className="header-actions">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="status-filter"
          >
            <option value="">All Orders</option>
            <option value="paid">Awaiting Assignment</option>
            <option value="assigned">Assigned</option>
            <option value="delivered">Delivered</option>
          </select>
          <button onClick={fetchOrders} className="refresh-btn">
            🔄 Refresh
          </button>
        </div>
      </header>

      {paidOrders.length > 0 && (
        <section className="orders-section urgent">
          <h2>⚡ Awaiting Assignment ({paidOrders.length})</h2>
          <div className="orders-grid">
            {paidOrders.map((order) => (
              <div
                key={order.id}
                className="order-card clickable"
                onClick={() => navigate(`/manager/orders/${order.id}`)}
              >
                <div className="order-header">
                  <span className="order-id">Order #{order.id}</span>
                  <span className={`status-badge ${getStatusClass(order.status)}`}>
                    {order.status.toUpperCase()}
                  </span>
                </div>
                <div className="order-body">
                  <p className="order-address">📍 {order.delivery_address || 'No address'}</p>
                  <p className="order-items">
                    {order.ordered_dishes.length} item(s)
                  </p>
                  <p className="order-total">Total: {formatCents(order.finalCost)}</p>
                </div>
                <div className="order-footer">
                  <span className="order-date">
                    {order.dateTime ? new Date(order.dateTime).toLocaleString() : 'N/A'}
                  </span>
                  <button className="view-btn">View Bids →</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {otherOrders.length > 0 && (
        <section className="orders-section">
          <h2>All Orders ({otherOrders.length})</h2>
          <div className="orders-grid">
            {otherOrders.map((order) => (
              <div
                key={order.id}
                className="order-card clickable"
                onClick={() => navigate(`/manager/orders/${order.id}`)}
              >
                <div className="order-header">
                  <span className="order-id">Order #{order.id}</span>
                  <span className={`status-badge ${getStatusClass(order.status)}`}>
                    {order.status.toUpperCase()}
                  </span>
                </div>
                <div className="order-body">
                  <p className="order-address">📍 {order.delivery_address || 'No address'}</p>
                  <p className="order-items">
                    {order.ordered_dishes.length} item(s)
                  </p>
                  <p className="order-total">Total: {formatCents(order.finalCost)}</p>
                </div>
                <div className="order-footer">
                  <span className="order-date">
                    {order.dateTime ? new Date(order.dateTime).toLocaleString() : 'N/A'}
                  </span>
                  <button className="view-btn">View Details →</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {orders.length === 0 && (
        <div className="no-orders">
          <p>No orders found.</p>
        </div>
      )}
    </div>
  );
}

export default ManagerOrders;
