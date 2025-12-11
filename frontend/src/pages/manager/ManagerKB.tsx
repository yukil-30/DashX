import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import './ManagerKB.css';

interface KBEntry {
  id: number;
  question: string;
  answer: string;
  keywords: string | null;
  confidence: number;
  author_id: number | null;
  author_email: string | null;
  is_active: boolean;
  flagged_count: number;
  avg_rating: number | null;
  created_at: string | null;
}

interface KBListResponse {
  entries: KBEntry[];
  total: number;
  flagged_count: number;
}

interface FlaggedChat {
  id: number;
  user_id: number;
  user_email: string | null;
  question: string;
  answer: string;
  source: string;
  confidence: number | null;
  rating: number;
  kb_entry_id: number | null;
  created_at: string | null;
  reviewed: boolean;
}

interface FlaggedListResponse {
  flagged_chats: FlaggedChat[];
  total: number;
}

interface KBContribution {
  id: number;
  submitter_id: number;
  submitter_email: string | null;
  question: string;
  answer: string;
  keywords: string | null;
  status: 'pending' | 'approved' | 'rejected';
  rejection_reason: string | null;
  reviewed_by: number | null;
  reviewer_email: string | null;
  reviewed_at: string | null;
  created_kb_entry_id: number | null;
  created_at: string | null;
}

interface ContributionListResponse {
  contributions: KBContribution[];
  total: number;
  pending_count: number;
}

export function ManagerKB() {
  const [entries, setEntries] = useState<KBEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [flaggedCount, setFlaggedCount] = useState(0);
  const [flaggedChats, setFlaggedChats] = useState<FlaggedChat[]>([]);
  const [contributions, setContributions] = useState<KBContribution[]>([]);
  const [pendingContributions, setPendingContributions] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'entries' | 'flagged' | 'contributions'>('entries');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<KBEntry | null>(null);
  const [selectedFlagged, setSelectedFlagged] = useState<FlaggedChat | null>(null);
  const [selectedContribution, setSelectedContribution] = useState<KBContribution | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [confidenceLevel, setConfidenceLevel] = useState(0.8);

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 100 };
      params.include_inactive = includeInactive;
      params.flagged_only = flaggedOnly;
      
      const response = await apiClient.get<KBListResponse>('/manager/kb/moderation', { params });
      setEntries(response.data.entries);
      setTotal(response.data.total);
      setFlaggedCount(response.data.flagged_count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load KB entries');
    } finally {
      setLoading(false);
    }
  }, [includeInactive, flaggedOnly]);

  const fetchFlagged = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<FlaggedListResponse>('/chat/flagged');
      setFlaggedChats(response.data.flagged_chats);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load flagged chats');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchContributions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<ContributionListResponse>('/chat/kb/contributions', {
        params: { status_filter: 'pending' }
      });
      setContributions(response.data.contributions);
      setPendingContributions(response.data.pending_count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load contributions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'entries') {
      fetchEntries();
    } else if (activeTab === 'flagged') {
      fetchFlagged();
    } else if (activeTab === 'contributions') {
      fetchContributions();
    }
  }, [activeTab, fetchEntries, fetchFlagged, fetchContributions]);

  // Also fetch contribution count on initial load
  useEffect(() => {
    const fetchPendingCount = async () => {
      try {
        const response = await apiClient.get<ContributionListResponse>('/chat/kb/contributions', {
          params: { status_filter: 'pending', limit: 1 }
        });
        setPendingContributions(response.data.pending_count);
      } catch (err) {
        // Silently fail
      }
    };
    fetchPendingCount();
  }, []);

  const handleRemoveEntry = async (entryId: number, permanent: boolean = false) => {
    try {
      await apiClient.delete(`/manager/kb/${entryId}`, {
        params: { permanent }
      });
      setSuccessMessage(`KB entry ${permanent ? 'permanently deleted' : 'deactivated'}`);
      fetchEntries();
      setSelectedEntry(null);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove entry');
    }
  };

  const handleRestoreEntry = async (entryId: number) => {
    try {
      await apiClient.post(`/manager/kb/${entryId}/restore`);
      setSuccessMessage('KB entry restored');
      fetchEntries();
      setSelectedEntry(null);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to restore entry');
    }
  };

  const handleReviewFlagged = async (chatId: number, action: 'dismiss' | 'remove_kb' | 'disable_author') => {
    try {
      await apiClient.post(`/chat/${chatId}/review`, { action });
      setSuccessMessage(`Flagged chat reviewed (${action})`);
      fetchFlagged();
      setSelectedFlagged(null);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to review flagged chat');
    }
  };

  const handleApproveContribution = async (contributionId: number) => {
    try {
      await apiClient.post(`/chat/kb/contributions/${contributionId}/review`, {
        action: 'approve',
        confidence: confidenceLevel
      });
      setSuccessMessage('Contribution approved and added to KB');
      fetchContributions();
      setSelectedContribution(null);
      setConfidenceLevel(0.8);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to approve contribution');
    }
  };

  const handleRejectContribution = async (contributionId: number) => {
    if (!rejectionReason.trim()) {
      setError('Rejection reason is required');
      return;
    }
    try {
      await apiClient.post(`/chat/kb/contributions/${contributionId}/review`, {
        action: 'reject',
        rejection_reason: rejectionReason
      });
      setSuccessMessage('Contribution rejected');
      fetchContributions();
      setSelectedContribution(null);
      setRejectionReason('');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reject contribution');
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="manager-kb">
      <header className="page-header">
        <div className="header-left">
          <Link to="/manager/dashboard" className="back-link">← Dashboard</Link>
          <h1>📚 KB Moderation</h1>
        </div>
        <div className="header-stats">
          <span className={`stat ${flaggedCount > 0 ? 'warning' : ''}`}>
            🚩 {flaggedCount} Flagged
          </span>
          <span className="stat">{total} Total Entries</span>
        </div>
      </header>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'entries' ? 'active' : ''}`}
          onClick={() => setActiveTab('entries')}
        >
          📖 KB Entries
        </button>
        <button
          className={`tab ${activeTab === 'flagged' ? 'active' : ''}`}
          onClick={() => setActiveTab('flagged')}
        >
          🚩 Flagged Chats
          {flaggedChats.length > 0 && (
            <span className="tab-badge">{flaggedChats.length}</span>
          )}
        </button>
        <button
          className={`tab ${activeTab === 'contributions' ? 'active' : ''}`}
          onClick={() => setActiveTab('contributions')}
        >
          📝 Contributions
          {pendingContributions > 0 && (
            <span className="tab-badge">{pendingContributions}</span>
          )}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {successMessage && (
        <div className="success-banner">
          {successMessage}
          <button onClick={() => setSuccessMessage(null)}>✕</button>
        </div>
      )}

      {activeTab === 'entries' && (
        <>
          <div className="controls">
            <div className="filters">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={includeInactive}
                  onChange={(e) => setIncludeInactive(e.target.checked)}
                />
                Include Inactive
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={flaggedOnly}
                  onChange={(e) => setFlaggedOnly(e.target.checked)}
                />
                Flagged Only
              </label>
            </div>
            <button onClick={fetchEntries} className="btn-refresh">🔄 Refresh</button>
          </div>

          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
            </div>
          ) : (
            <div className="entries-grid">
              {entries.length === 0 ? (
                <div className="empty-state">
                  <p>No KB entries found</p>
                </div>
              ) : (
                entries.map((entry) => (
                  <div
                    key={entry.id}
                    className={`entry-card ${!entry.is_active ? 'inactive' : ''} ${entry.flagged_count > 0 ? 'flagged' : ''}`}
                    onClick={() => setSelectedEntry(entry)}
                  >
                    <div className="entry-header">
                      <span className="entry-id">#{entry.id}</span>
                      <div className="entry-badges">
                        {!entry.is_active && <span className="badge inactive">Inactive</span>}
                        {entry.flagged_count > 0 && (
                          <span className="badge flagged">🚩 {entry.flagged_count}</span>
                        )}
                        {entry.avg_rating !== null && (
                          <span className={`badge rating ${entry.avg_rating >= 3 ? 'good' : 'poor'}`}>
                            ⭐ {entry.avg_rating.toFixed(1)}
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="entry-question">{entry.question}</p>
                    <p className="entry-answer">{entry.answer.substring(0, 150)}...</p>
                    <div className="entry-footer">
                      <span className="confidence">
                        Confidence: {(entry.confidence * 100).toFixed(0)}%
                      </span>
                      {entry.author_email && (
                        <span className="author">By: {entry.author_email}</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'flagged' && (
        <>
          <div className="controls">
            <button onClick={fetchFlagged} className="btn-refresh">🔄 Refresh</button>
          </div>

          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
            </div>
          ) : (
            <div className="flagged-list">
              {flaggedChats.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">✅</span>
                  <p>No flagged chats to review</p>
                </div>
              ) : (
                flaggedChats.map((chat) => (
                  <div
                    key={chat.id}
                    className="flagged-card"
                    onClick={() => setSelectedFlagged(chat)}
                  >
                    <div className="flagged-header">
                      <span className="flagged-id">Chat #{chat.id}</span>
                      <span className="flagged-source">Source: {chat.source}</span>
                    </div>
                    <div className="flagged-content">
                      <p className="flagged-question">
                        <strong>Q:</strong> {chat.question}
                      </p>
                      <p className="flagged-answer">
                        <strong>A:</strong> {chat.answer.substring(0, 200)}...
                      </p>
                    </div>
                    <div className="flagged-footer">
                      <span className="flagged-user">User: {chat.user_email || `#${chat.user_id}`}</span>
                      <span className="flagged-date">{formatDate(chat.created_at)}</span>
                    </div>
                    {chat.kb_entry_id && (
                      <span className="kb-link">KB Entry: #{chat.kb_entry_id}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      {/* Contributions Tab */}
      {activeTab === 'contributions' && (
        <>
          <div className="controls">
            <button onClick={fetchContributions} className="btn-refresh">🔄 Refresh</button>
          </div>

          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
            </div>
          ) : (
            <div className="flagged-list">
              {contributions.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">✅</span>
                  <p>No pending contributions to review</p>
                </div>
              ) : (
                contributions.map((contribution) => (
                  <div
                    key={contribution.id}
                    className="flagged-card"
                    onClick={() => setSelectedContribution(contribution)}
                  >
                    <div className="flagged-header">
                      <span className="flagged-id">Contribution #{contribution.id}</span>
                      <span className={`badge ${contribution.status === 'pending' ? 'warning' : contribution.status === 'approved' ? 'success' : 'danger'}`}>
                        {contribution.status}
                      </span>
                    </div>
                    <div className="flagged-content">
                      <p className="flagged-question">
                        <strong>Q:</strong> {contribution.question}
                      </p>
                      <p className="flagged-answer">
                        <strong>A:</strong> {contribution.answer.substring(0, 200)}...
                      </p>
                    </div>
                    <div className="flagged-footer">
                      <span className="flagged-user">Submitted by: {contribution.submitter_email || `#${contribution.submitter_id}`}</span>
                      <span className="flagged-date">{formatDate(contribution.created_at)}</span>
                    </div>
                    {contribution.keywords && (
                      <span className="kb-link">Keywords: {contribution.keywords}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      {/* Entry Detail Modal */}
      {selectedEntry && (
        <div className="modal-overlay" onClick={() => setSelectedEntry(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>KB Entry #{selectedEntry.id}</h3>
            
            <div className="modal-section">
              <label>Question</label>
              <p className="modal-text">{selectedEntry.question}</p>
            </div>

            <div className="modal-section">
              <label>Answer</label>
              <p className="modal-text">{selectedEntry.answer}</p>
            </div>

            <div className="modal-meta">
              <span>Confidence: {(selectedEntry.confidence * 100).toFixed(0)}%</span>
              <span>Keywords: {selectedEntry.keywords || 'None'}</span>
              <span>Author: {selectedEntry.author_email || 'Unknown'}</span>
              <span>Status: {selectedEntry.is_active ? 'Active' : 'Inactive'}</span>
              {selectedEntry.avg_rating !== null && (
                <span>Avg Rating: {selectedEntry.avg_rating.toFixed(1)}</span>
              )}
              <span>Flags: {selectedEntry.flagged_count}</span>
            </div>

            <div className="modal-actions">
              {selectedEntry.is_active ? (
                <>
                  <button
                    onClick={() => handleRemoveEntry(selectedEntry.id, false)}
                    className="btn-deactivate"
                  >
                    🚫 Deactivate
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Permanently delete this entry?')) {
                        handleRemoveEntry(selectedEntry.id, true);
                      }
                    }}
                    className="btn-delete"
                  >
                    🗑️ Delete Permanently
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleRestoreEntry(selectedEntry.id)}
                  className="btn-restore"
                >
                  ♻️ Restore
                </button>
              )}
            </div>

            <button onClick={() => setSelectedEntry(null)} className="btn-close">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Flagged Chat Modal */}
      {selectedFlagged && (
        <div className="modal-overlay" onClick={() => setSelectedFlagged(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>🚩 Review Flagged Chat #{selectedFlagged.id}</h3>
            
            <div className="modal-section">
              <label>User Question</label>
              <p className="modal-text">{selectedFlagged.question}</p>
            </div>

            <div className="modal-section">
              <label>System Answer</label>
              <p className="modal-text">{selectedFlagged.answer}</p>
            </div>

            <div className="modal-meta">
              <span>Source: {selectedFlagged.source}</span>
              <span>User: {selectedFlagged.user_email || `#${selectedFlagged.user_id}`}</span>
              <span>Rating: {selectedFlagged.rating} (flagged)</span>
              {selectedFlagged.kb_entry_id && (
                <span>KB Entry: #{selectedFlagged.kb_entry_id}</span>
              )}
            </div>

            <div className="review-actions">
              <button
                onClick={() => handleReviewFlagged(selectedFlagged.id, 'dismiss')}
                className="review-btn dismiss"
              >
                ✓ Dismiss
                <span>No action needed</span>
              </button>
              {selectedFlagged.kb_entry_id && (
                <button
                  onClick={() => handleReviewFlagged(selectedFlagged.id, 'remove_kb')}
                  className="review-btn remove-kb"
                >
                  🚫 Remove KB Entry
                  <span>Deactivate source entry</span>
                </button>
              )}
              {selectedFlagged.kb_entry_id && (
                <button
                  onClick={() => handleReviewFlagged(selectedFlagged.id, 'disable_author')}
                  className="review-btn disable-author"
                >
                  🔒 Disable Author
                  <span>Deactivate all entries by author</span>
                </button>
              )}
            </div>

            <button onClick={() => setSelectedFlagged(null)} className="btn-close">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Contribution Review Modal */}
      {selectedContribution && (
        <div className="modal-overlay" onClick={() => setSelectedContribution(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>📝 Review Contribution #{selectedContribution.id}</h3>
            
            <div className="modal-section">
              <label>Question</label>
              <p className="modal-text">{selectedContribution.question}</p>
            </div>

            <div className="modal-section">
              <label>Answer</label>
              <p className="modal-text">{selectedContribution.answer}</p>
            </div>

            <div className="modal-meta">
              <span>Submitted by: {selectedContribution.submitter_email || `#${selectedContribution.submitter_id}`}</span>
              <span>Keywords: {selectedContribution.keywords || 'None'}</span>
              <span>Submitted: {formatDate(selectedContribution.created_at)}</span>
            </div>

            {selectedContribution.status === 'pending' && (
              <>
                <div className="modal-section">
                  <label>Confidence Level (for approval)</label>
                  <input
                    type="range"
                    min="0.5"
                    max="1"
                    step="0.05"
                    value={confidenceLevel}
                    onChange={(e) => setConfidenceLevel(parseFloat(e.target.value))}
                    className="confidence-slider"
                  />
                  <span className="confidence-value">{(confidenceLevel * 100).toFixed(0)}%</span>
                </div>

                <div className="modal-section">
                  <label>Rejection Reason (required for rejection)</label>
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Enter reason for rejection..."
                    className="rejection-input"
                  />
                </div>

                <div className="review-actions">
                  <button
                    onClick={() => handleApproveContribution(selectedContribution.id)}
                    className="review-btn approve"
                  >
                    ✅ Approve
                    <span>Add to knowledge base</span>
                  </button>
                  <button
                    onClick={() => handleRejectContribution(selectedContribution.id)}
                    className="review-btn reject"
                  >
                    ❌ Reject
                    <span>Decline this contribution</span>
                  </button>
                </div>
              </>
            )}

            {selectedContribution.status !== 'pending' && (
              <div className="modal-section">
                <p className={`status-message ${selectedContribution.status}`}>
                  This contribution has been {selectedContribution.status}.
                  {selectedContribution.rejection_reason && (
                    <span className="rejection-reason">
                      Reason: {selectedContribution.rejection_reason}
                    </span>
                  )}
                </p>
              </div>
            )}

            <button onClick={() => setSelectedContribution(null)} className="btn-close">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ManagerKB;
