import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import './ManagerDashboard.css';

interface DashboardStats {
  pending_complaints: number;
  pending_disputes: number;
  orders_awaiting_assignment: number;
  flagged_kb_items: number;
  unread_notifications: number;
  total_employees: number;
  chefs_count: number;
  delivery_count: number;
  employees_at_risk: number;
  restaurant_id: number | null;
  restaurant_name: string | null;
  total_orders: number;
  orders_today: number;
  revenue_today_cents: number;
  total_customers: number;
  total_vips: number;
}

export function ManagerDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const response = await apiClient.get<DashboardStats>('/manager/dashboard');
      setStats(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const formatCurrency = (cents: number) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  if (loading) {
    return (
      <div className="manager-dashboard">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="manager-dashboard">
        <div className="error-container">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
          <button onClick={fetchDashboard} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="manager-dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>👨‍💼 Manager Dashboard</h1>
          {stats.restaurant_name && (
            <span className="restaurant-badge">{stats.restaurant_name}</span>
          )}
        </div>
        <button onClick={fetchDashboard} className="refresh-btn">
          🔄 Refresh
        </button>
      </header>

      {/* Pending Actions */}
      <section className="pending-actions">
        <h2>⏳ Pending Actions</h2>
        <div className="action-cards">
          <Link to="/manager/complaints" className="action-card warning">
            <div className="card-icon">⚠️</div>
            <div className="card-content">
              <span className="card-number">{stats.pending_complaints}</span>
              <span className="card-label">Pending Complaints</span>
            </div>
          </Link>

          <Link to="/manager/disputes" className="action-card danger">
            <div className="card-icon">🔥</div>
            <div className="card-content">
              <span className="card-number">{stats.pending_disputes}</span>
              <span className="card-label">Disputes to Resolve</span>
            </div>
          </Link>

          <Link to="/manager/bidding" className="action-card info">
            <div className="card-icon">🚗</div>
            <div className="card-content">
              <span className="card-number">{stats.orders_awaiting_assignment}</span>
              <span className="card-label">Orders Need Assignment</span>
            </div>
          </Link>

          <Link to="/manager/kb" className="action-card">
            <div className="card-icon">🤖</div>
            <div className="card-content">
              <span className="card-number">{stats.flagged_kb_items}</span>
              <span className="card-label">Flagged KB Items</span>
            </div>
          </Link>

          <div className="action-card">
            <div className="card-icon">🔔</div>
            <div className="card-content">
              <span className="card-number">{stats.unread_notifications}</span>
              <span className="card-label">Unread Notifications</span>
            </div>
          </div>
        </div>
      </section>

      {/* Employee Overview */}
      <section className="employees-section">
        <div className="section-header">
          <h2>👥 Employees</h2>
          <Link to="/manager/employees" className="view-all-btn">
            Manage Employees →
          </Link>
        </div>
        <div className="stats-grid">
          <div className="stat-box">
            <span className="stat-value">{stats.total_employees}</span>
            <span className="stat-label">Total Employees</span>
          </div>
          <div className="stat-box">
            <span className="stat-icon">👨‍🍳</span>
            <span className="stat-value">{stats.chefs_count}</span>
            <span className="stat-label">Chefs</span>
          </div>
          <div className="stat-box">
            <span className="stat-icon">🛵</span>
            <span className="stat-value">{stats.delivery_count}</span>
            <span className="stat-label">Delivery</span>
          </div>
          <div className={`stat-box ${stats.employees_at_risk > 0 ? 'at-risk' : ''}`}>
            <span className="stat-value">{stats.employees_at_risk}</span>
            <span className="stat-label">At Risk</span>
          </div>
        </div>
      </section>

      {/* Restaurant Statistics */}
      <section className="restaurant-stats">
        <h2>📊 Restaurant Statistics</h2>
        <div className="stats-grid large">
          <div className="stat-box highlight">
            <span className="stat-value">{formatCurrency(stats.revenue_today_cents)}</span>
            <span className="stat-label">Today's Revenue</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.orders_today}</span>
            <span className="stat-label">Orders Today</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.total_orders}</span>
            <span className="stat-label">Total Orders</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.total_customers}</span>
            <span className="stat-label">Customers</span>
          </div>
          <div className="stat-box vip">
            <span className="stat-icon">⭐</span>
            <span className="stat-value">{stats.total_vips}</span>
            <span className="stat-label">VIP Members</span>
          </div>
        </div>
      </section>

      {/* Quick Actions */}
      <section className="quick-actions">
        <h2>⚡ Quick Actions</h2>
        <div className="actions-grid">
          <Link to="/manager/employees/create" className="quick-action-btn">
            <span className="action-icon">➕</span>
            <span>Create Employee</span>
          </Link>
          <Link to="/manager/orders" className="quick-action-btn">
            <span className="action-icon">📦</span>
            <span>View All Orders</span>
          </Link>
          <Link to="/manager/employees/evaluate" className="quick-action-btn">
            <span className="action-icon">📋</span>
            <span>Evaluate Employees</span>
          </Link>
          <Link to="/manager/kb" className="quick-action-btn">
            <span className="action-icon">📚</span>
            <span>Manage KB</span>
          </Link>
        </div>
      </section>
    </div>
  );
}

export default ManagerDashboard;
