import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import './ManagerDisputes.css';

interface Dispute {
  complaint_id: number;
  complaint_type: string;
  description: string;
  filer_id: number;
  filer_email: string;
  about_id: number | null;
  about_email: string | null;
  about_type: string | null;
  order_id: number | null;
  status: string;
  is_disputed: boolean;
  dispute_reason: string | null;
  filer_warnings: number;
  about_warnings: number;
  about_complaints_count: number;
  about_compliments_count: number;
  created_at: string | null;
}

interface DisputeListResponse {
  disputes: Dispute[];
  total: number;
  pending_count: number;
}

interface ResolveResult {
  message: string;
  complaint_id: number;
  resolution: string;
  warning_applied_to: number | null;
  new_warning_count: number | null;
  vip_downgrade: boolean;
  blacklisted: boolean;
  employee_demoted: boolean;
  employee_fired: boolean;
  audit_log_id: number;
}

export function ManagerDisputes() {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [total, setTotal] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedDispute, setSelectedDispute] = useState<Dispute | null>(null);
  const [resolving, setResolving] = useState(false);
  const [resolveNotes, setResolveNotes] = useState('');
  const [resolveResult, setResolveResult] = useState<ResolveResult | null>(null);

  const fetchDisputes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 50 };
      if (statusFilter) params.status_filter = statusFilter;
      
      const response = await apiClient.get<DisputeListResponse>('/manager/disputes', { params });
      setDisputes(response.data.disputes);
      setTotal(response.data.total);
      setPendingCount(response.data.pending_count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load disputes');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchDisputes();
  }, [fetchDisputes]);

  const handleResolve = async (resolution: 'uphold' | 'dismiss') => {
    if (!selectedDispute) return;
    
    setResolving(true);
    setResolveResult(null);
    
    try {
      const response = await apiClient.post<ResolveResult>(
        `/manager/disputes/${selectedDispute.complaint_id}/resolve`,
        { resolution, notes: resolveNotes || null }
      );
      
      setResolveResult(response.data);
      
      // Refresh after showing result
      setTimeout(() => {
        fetchDisputes();
        setSelectedDispute(null);
        setResolveNotes('');
        setResolveResult(null);
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resolve dispute');
    } finally {
      setResolving(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const getTypeBadge = (type: string) => {
    return type === 'complaint' ? (
      <span className="type-badge complaint">⚠️ Complaint</span>
    ) : (
      <span className="type-badge compliment">👍 Compliment</span>
    );
  };

  const getStatusBadge = (status: string, isDisputed: boolean) => {
    if (isDisputed || status === 'disputed') {
      return <span className="status-badge disputed">🔥 Disputed</span>;
    }
    if (status === 'pending') {
      return <span className="status-badge pending">⏳ Pending</span>;
    }
    return <span className="status-badge resolved">✓ Resolved</span>;
  };

  const getRoleBadge = (type: string | null) => {
    if (!type) return null;
    switch (type) {
      case 'chef':
        return <span className="role-badge chef">👨‍🍳 Chef</span>;
      case 'delivery':
        return <span className="role-badge delivery">🛵 Delivery</span>;
      case 'customer':
        return <span className="role-badge customer">👤 Customer</span>;
      case 'vip':
        return <span className="role-badge vip">⭐ VIP</span>;
      default:
        return <span className="role-badge">{type}</span>;
    }
  };

  return (
    <div className="manager-disputes">
      <header className="page-header">
        <div className="header-left">
          <Link to="/manager/dashboard" className="back-link">← Dashboard</Link>
          <h1>⚖️ Dispute Resolution</h1>
        </div>
        <div className="header-stats">
          <span className="stat pending">{pendingCount} Pending</span>
          <span className="stat">{total} Total</span>
        </div>
      </header>

      <div className="controls">
        <div className="filters">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">Pending & Disputed</option>
            <option value="pending">Pending Only</option>
            <option value="disputed">Disputed Only</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
        
        <button onClick={fetchDisputes} className="btn-refresh">
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading disputes...</p>
        </div>
      ) : (
        <div className="disputes-list">
          {disputes.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">✅</span>
              <h3>No pending disputes</h3>
              <p>All disputes have been resolved.</p>
            </div>
          ) : (
            disputes.map((dispute) => (
              <div
                key={dispute.complaint_id}
                className={`dispute-card ${dispute.is_disputed ? 'disputed' : ''}`}
                onClick={() => setSelectedDispute(dispute)}
              >
                <div className="dispute-header">
                  <div className="dispute-badges">
                    {getTypeBadge(dispute.complaint_type)}
                    {getStatusBadge(dispute.status, dispute.is_disputed)}
                  </div>
                  <span className="dispute-date">{formatDate(dispute.created_at)}</span>
                </div>

                <div className="dispute-body">
                  <p className="dispute-description">{dispute.description}</p>
                </div>

                <div className="dispute-parties">
                  <div className="party filed-by">
                    <span className="party-label">Filed by:</span>
                    <span className="party-email">{dispute.filer_email}</span>
                    <span className="party-warnings">
                      ⚠️ {dispute.filer_warnings} warnings
                    </span>
                  </div>
                  
                  {dispute.about_id && (
                    <div className="party about">
                      <span className="party-label">About:</span>
                      <span className="party-email">{dispute.about_email}</span>
                      {getRoleBadge(dispute.about_type)}
                      <div className="party-stats">
                        <span className="complaint-count">
                          ⚠️ {dispute.about_complaints_count}
                        </span>
                        <span className="compliment-count">
                          👍 {dispute.about_compliments_count}
                        </span>
                        <span className="warning-count">
                          🚨 {dispute.about_warnings} warnings
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {dispute.order_id && (
                  <div className="dispute-order">
                    <Link to={`/manager/orders/${dispute.order_id}`} onClick={(e) => e.stopPropagation()}>
                      📦 View Order #{dispute.order_id}
                    </Link>
                  </div>
                )}

                <div className="dispute-action-hint">
                  Click to resolve →
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Resolution Modal */}
      {selectedDispute && (
        <div className="modal-overlay" onClick={() => setSelectedDispute(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>⚖️ Resolve Dispute #{selectedDispute.complaint_id}</h3>
            
            <div className="modal-section">
              <h4>Complaint Details</h4>
              <p className="complaint-text">{selectedDispute.description}</p>
              <div className="complaint-meta">
                {getTypeBadge(selectedDispute.complaint_type)}
                {selectedDispute.is_disputed && <span className="disputed-label">🔥 Disputed by subject</span>}
              </div>
            </div>

            <div className="modal-section parties-section">
              <div className="party-box filer">
                <h4>Filer</h4>
                <p className="party-email">{selectedDispute.filer_email}</p>
                <p className="party-detail">Current warnings: <strong>{selectedDispute.filer_warnings}</strong></p>
                <p className="impact-warning">
                  If dismissed: +1 warning → {selectedDispute.filer_warnings + 1} total
                </p>
              </div>
              
              {selectedDispute.about_id && (
                <div className="party-box about">
                  <h4>Subject</h4>
                  <p className="party-email">{selectedDispute.about_email}</p>
                  {getRoleBadge(selectedDispute.about_type)}
                  <p className="party-detail">
                    Complaints: {selectedDispute.about_complaints_count} | 
                    Compliments: {selectedDispute.about_compliments_count}
                  </p>
                  <p className="party-detail">Current warnings: <strong>{selectedDispute.about_warnings}</strong></p>
                  <p className="impact-warning">
                    If upheld: +1 warning → {selectedDispute.about_warnings + 1} total
                    {selectedDispute.about_type === 'vip' && selectedDispute.about_warnings + 1 >= 2 && (
                      <span className="impact-danger"> (VIP DOWNGRADE!)</span>
                    )}
                    {selectedDispute.about_type === 'customer' && selectedDispute.about_warnings + 1 >= 3 && (
                      <span className="impact-danger"> (BLACKLIST!)</span>
                    )}
                    {['chef', 'delivery'].includes(selectedDispute.about_type || '') && selectedDispute.about_complaints_count + 1 >= 3 && (
                      <span className="impact-danger"> (DEMOTION!)</span>
                    )}
                  </p>
                </div>
              )}
            </div>

            <div className="modal-section">
              <label>Resolution Notes (optional)</label>
              <textarea
                value={resolveNotes}
                onChange={(e) => setResolveNotes(e.target.value)}
                placeholder="Add any notes about this decision..."
                rows={3}
              />
            </div>

            {resolveResult && (
              <div className="resolve-result">
                <h4>✓ Resolution Applied</h4>
                <p>{resolveResult.message}</p>
                {resolveResult.warning_applied_to && (
                  <p>Warning applied to user #{resolveResult.warning_applied_to} (now {resolveResult.new_warning_count} warnings)</p>
                )}
                {resolveResult.vip_downgrade && <p className="impact-alert">⚠️ VIP was downgraded to customer</p>}
                {resolveResult.blacklisted && <p className="impact-alert">🚫 User was blacklisted</p>}
                {resolveResult.employee_demoted && <p className="impact-alert">📉 Employee was demoted</p>}
                {resolveResult.employee_fired && <p className="impact-alert">🔥 Employee was fired</p>}
              </div>
            )}

            {!resolveResult && (
              <div className="resolution-buttons">
                <button
                  onClick={() => handleResolve('uphold')}
                  className="resolve-btn uphold"
                  disabled={resolving}
                >
                  ✓ Uphold Complaint
                  <span className="btn-subtitle">Subject gets warning</span>
                </button>
                <button
                  onClick={() => handleResolve('dismiss')}
                  className="resolve-btn dismiss"
                  disabled={resolving}
                >
                  ✕ Dismiss Complaint
                  <span className="btn-subtitle">Filer gets warning</span>
                </button>
              </div>
            )}

            <button
              onClick={() => {
                setSelectedDispute(null);
                setResolveNotes('');
                setResolveResult(null);
              }}
              className="close-btn"
            >
              {resolveResult ? 'Done' : 'Cancel'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ManagerDisputes;
