import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../lib/api-client';
import './ManagerComplaints.css';

interface Complaint {
  id: number;
  accountID: number | null;
  type: 'complaint' | 'compliment';
  description: string;
  filer: number;
  filer_email: string | null;
  about_email: string | null;
  order_id: number | null;
  status: string;
  resolution: string | null;
  resolved_by: number | null;
  resolved_at: string | null;
  created_at: string | null;
}

interface ComplaintListResponse {
  complaints: Complaint[];
  total: number;
  unresolved_count: number;
}

interface ResolveResponse {
  message: string;
  complaint_id: number;
  resolution: string;
  warning_applied_to: number | null;
  warning_count: number | null;
  account_status_changed: string | null;
  audit_log_id: number;
}

interface ManagerComplaintsProps {
  token?: string;
}

export function ManagerComplaints(_props: ManagerComplaintsProps) {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [total, setTotal] = useState(0);
  const [unresolvedCount, setUnresolvedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);
  const [resolving, setResolving] = useState(false);
  const [resolveNotes, setResolveNotes] = useState('');
  const [resolveResult, setResolveResult] = useState<ResolveResponse | null>(null);

  const fetchComplaints = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 50 };
      if (statusFilter) params.status_filter = statusFilter;
      if (typeFilter) params.type_filter = typeFilter;
      
      const response = await apiClient.get<ComplaintListResponse>('/complaints', { params });
      setComplaints(response.data.complaints);
      setTotal(response.data.total);
      setUnresolvedCount(response.data.unresolved_count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load complaints');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter]);

  useEffect(() => {
    fetchComplaints();
  }, [fetchComplaints]);

  const handleResolve = async (resolution: 'dismissed' | 'warning_issued') => {
    if (!selectedComplaint) return;
    
    setResolving(true);
    setResolveResult(null);
    
    try {
      const response = await apiClient.patch<ResolveResponse>(
        `/complaints/${selectedComplaint.id}/resolve`,
        {
          resolution,
          notes: resolveNotes || null,
        }
      );
      
      setResolveResult(response.data);
      
      // Refresh the list after resolving
      setTimeout(() => {
        fetchComplaints();
        setSelectedComplaint(null);
        setResolveNotes('');
        setResolveResult(null);
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resolve complaint');
    } finally {
      setResolving(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const getTypeIcon = (type: string) => {
    return type === 'complaint' ? '⚠️' : '👍';
  };

  const getStatusBadge = (status: string, resolution: string | null) => {
    if (status === 'pending') {
      return <span className="status-badge pending">Pending</span>;
    }
    if (resolution === 'dismissed') {
      return <span className="status-badge dismissed">Dismissed</span>;
    }
    if (resolution === 'warning_issued') {
      return <span className="status-badge warning">Warning Issued</span>;
    }
    if (resolution === 'canceled_by_compliment') {
      return <span className="status-badge canceled">Canceled</span>;
    }
    return <span className="status-badge resolved">Resolved</span>;
  };

  if (loading && complaints.length === 0) {
    return <div className="loading">Loading complaints...</div>;
  }

  return (
    <div className="manager-complaints">
      <header className="page-header">
        <h1>📋 Complaints & Reputation</h1>
        <div className="header-stats">
          <span className="stat">
            <strong>{unresolvedCount}</strong> unresolved
          </span>
          <span className="stat">
            <strong>{total}</strong> total
          </span>
        </div>
      </header>

      <div className="filters">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="filter-select"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="resolved">Resolved</option>
        </select>
        
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="filter-select"
        >
          <option value="">All Types</option>
          <option value="complaint">Complaints</option>
          <option value="compliment">Compliments</option>
        </select>
        
        <button onClick={fetchComplaints} className="refresh-btn">
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="complaints-container">
        <div className="complaints-list">
          {complaints.length === 0 ? (
            <div className="no-complaints">
              <p>No complaints found.</p>
            </div>
          ) : (
            complaints.map((complaint) => (
              <div
                key={complaint.id}
                className={`complaint-card ${selectedComplaint?.id === complaint.id ? 'selected' : ''} ${complaint.type}`}
                onClick={() => setSelectedComplaint(complaint)}
              >
                <div className="complaint-header">
                  <span className="complaint-type">
                    {getTypeIcon(complaint.type)} {complaint.type.toUpperCase()}
                  </span>
                  {getStatusBadge(complaint.status, complaint.resolution)}
                </div>
                
                <div className="complaint-body">
                  <p className="complaint-about">
                    {complaint.about_email ? (
                      <>About: <strong>{complaint.about_email}</strong></>
                    ) : (
                      <em>General complaint</em>
                    )}
                  </p>
                  <p className="complaint-from">
                    From: {complaint.filer_email || `User #${complaint.filer}`}
                  </p>
                  <p className="complaint-text">{complaint.description.substring(0, 100)}...</p>
                </div>
                
                <div className="complaint-footer">
                  <span className="complaint-date">
                    {formatDate(complaint.created_at)}
                  </span>
                  {complaint.order_id && (
                    <span className="complaint-order">
                      Order #{complaint.order_id}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {selectedComplaint && (
          <div className="complaint-detail">
            <h2>
              {getTypeIcon(selectedComplaint.type)} {selectedComplaint.type.toUpperCase()} #{selectedComplaint.id}
            </h2>
            
            <div className="detail-section">
              <h3>Details</h3>
              <dl>
                <dt>Filed By:</dt>
                <dd>{selectedComplaint.filer_email || `User #${selectedComplaint.filer}`}</dd>
                
                <dt>About:</dt>
                <dd>{selectedComplaint.about_email || 'General (no specific user)'}</dd>
                
                {selectedComplaint.order_id && (
                  <>
                    <dt>Related Order:</dt>
                    <dd>#{selectedComplaint.order_id}</dd>
                  </>
                )}
                
                <dt>Filed On:</dt>
                <dd>{formatDate(selectedComplaint.created_at)}</dd>
                
                <dt>Status:</dt>
                <dd>{getStatusBadge(selectedComplaint.status, selectedComplaint.resolution)}</dd>
              </dl>
            </div>
            
            <div className="detail-section">
              <h3>Description</h3>
              <p className="full-description">{selectedComplaint.description}</p>
            </div>
            
            {selectedComplaint.status === 'pending' && selectedComplaint.type === 'complaint' && (
              <div className="resolve-section">
                <h3>Resolve Complaint</h3>
                
                <div className="resolve-notes">
                  <label>Resolution Notes (optional):</label>
                  <textarea
                    value={resolveNotes}
                    onChange={(e) => setResolveNotes(e.target.value)}
                    placeholder="Add any notes about this resolution..."
                    rows={3}
                  />
                </div>
                
                <div className="resolve-actions">
                  <button
                    className="btn-dismiss"
                    onClick={() => handleResolve('dismissed')}
                    disabled={resolving}
                    title="Dismiss as without merit - complainant receives a warning"
                  >
                    {resolving ? '...' : '❌ Dismiss (Warn Complainant)'}
                  </button>
                  
                  <button
                    className="btn-warning"
                    onClick={() => handleResolve('warning_issued')}
                    disabled={resolving}
                    title="Issue warning to the person complained about"
                  >
                    {resolving ? '...' : '⚠️ Issue Warning'}
                  </button>
                </div>
                
                <div className="resolve-help">
                  <p><strong>Dismiss:</strong> Complaint without merit. The complainant will receive a warning.</p>
                  <p><strong>Issue Warning:</strong> Valid complaint. The target user will receive a warning.</p>
                </div>
              </div>
            )}
            
            {resolveResult && (
              <div className="resolve-result">
                <h3>✅ Resolution Complete</h3>
                <p>{resolveResult.message}</p>
                {resolveResult.warning_applied_to && (
                  <p>Warning applied to user #{resolveResult.warning_applied_to} (now has {resolveResult.warning_count} warnings)</p>
                )}
                {resolveResult.account_status_changed && (
                  <p className="status-change">
                    <strong>Account Status Changed:</strong> {resolveResult.account_status_changed}
                  </p>
                )}
                <p className="audit-ref">Audit Log Entry: #{resolveResult.audit_log_id}</p>
              </div>
            )}
            
            {selectedComplaint.status === 'resolved' && (
              <div className="resolution-info">
                <h3>Resolution</h3>
                <dl>
                  <dt>Resolution:</dt>
                  <dd>{selectedComplaint.resolution}</dd>
                  
                  <dt>Resolved By:</dt>
                  <dd>Manager #{selectedComplaint.resolved_by}</dd>
                  
                  <dt>Resolved At:</dt>
                  <dd>{formatDate(selectedComplaint.resolved_at)}</dd>
                </dl>
              </div>
            )}
            
            <button
              className="close-detail"
              onClick={() => {
                setSelectedComplaint(null);
                setResolveNotes('');
                setResolveResult(null);
              }}
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ManagerComplaints;
