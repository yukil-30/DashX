import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import apiClient from '../lib/api-client';
import { Complaint, ComplaintListResponse, DisputeRequest, DisputeResponse } from '../types/api';

interface ComplaintsListProps {
  mode: 'filed' | 'against';
  showDispute?: boolean;
}

export default function ComplaintsList({ mode, showDispute = false }: ComplaintsListProps) {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [unresolvedCount, setUnresolvedCount] = useState(0);
  const [disputingId, setDisputingId] = useState<number | null>(null);
  const [disputeReason, setDisputeReason] = useState('');

  useEffect(() => {
    fetchComplaints();
  }, [mode]);

  const fetchComplaints = async () => {
    setLoading(true);
    try {
      const endpoint = mode === 'filed' ? '/complaints/my/filed' : '/complaints/my/against';
      const response = await apiClient.get<ComplaintListResponse>(endpoint);
      setComplaints(response.data.complaints);
      setTotal(response.data.total);
      setUnresolvedCount(response.data.unresolved_count);
    } catch (err: any) {
      toast.error('Failed to load complaints');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDispute = async (complaintId: number) => {
    if (disputeReason.length < 10) {
      toast.error('Dispute reason must be at least 10 characters');
      return;
    }

    try {
      const request: DisputeRequest = { reason: disputeReason };
      await apiClient.post<DisputeResponse>(`/complaints/${complaintId}/dispute`, request);
      toast.success('Complaint disputed successfully. It will be reviewed by a manager.');
      setDisputingId(null);
      setDisputeReason('');
      fetchComplaints();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to dispute complaint');
    }
  };

  const getStatusBadge = (complaint: Complaint) => {
    if (complaint.disputed) {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">Disputed</span>;
    }
    switch (complaint.status) {
      case 'pending':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">Pending</span>;
      case 'resolved':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Resolved</span>;
      case 'disputed':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">Disputed</span>;
      default:
        return null;
    }
  };

  const getTypeBadge = (type: string) => {
    if (type === 'complaint') {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">⚠️ Complaint</span>;
    }
    return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">⭐ Compliment</span>;
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Stats */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {mode === 'filed' ? 'Complaints You Filed' : 'Complaints Against You'}
        </h3>
        <div className="flex gap-4 text-sm text-gray-600">
          <span>Total: {total}</span>
          <span className="text-yellow-600">Unresolved: {unresolvedCount}</span>
        </div>
      </div>

      {complaints.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          {mode === 'filed' 
            ? 'You haven\'t filed any complaints or compliments yet.'
            : 'No complaints or compliments filed against you.'}
        </div>
      ) : (
        <div className="space-y-4">
          {complaints.map((complaint) => (
            <div
              key={complaint.id}
              className={`bg-white rounded-lg shadow-md p-4 border-l-4 ${
                complaint.type === 'complaint' ? 'border-red-400' : 'border-green-400'
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {getTypeBadge(complaint.type)}
                  {getStatusBadge(complaint)}
                  {complaint.target_type && (
                    <span className="text-xs text-gray-500 capitalize">
                      ({complaint.target_type})
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(complaint.created_at).toLocaleDateString()}
                </span>
              </div>

              {/* Parties */}
              <div className="text-sm text-gray-600 mb-2">
                {mode === 'filed' ? (
                  <p>Against: <span className="font-medium">{complaint.about_email || 'General'}</span></p>
                ) : (
                  <p>Filed by: <span className="font-medium">{complaint.filer_email || 'Unknown'}</span></p>
                )}
                {complaint.order_id && (
                  <p>Order: #{complaint.order_id}</p>
                )}
              </div>

              {/* Description */}
              <p className="text-gray-800 mb-3">{complaint.description}</p>

              {/* Resolution */}
              {complaint.status === 'resolved' && complaint.resolution && (
                <div className="bg-gray-50 rounded-lg p-3 text-sm">
                  <span className="font-medium">Resolution:</span> {complaint.resolution}
                  {complaint.resolved_at && (
                    <span className="text-gray-500 ml-2">
                      on {new Date(complaint.resolved_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              )}

              {/* Dispute Section */}
              {complaint.disputed && complaint.dispute_reason && (
                <div className="bg-orange-50 rounded-lg p-3 text-sm mt-2">
                  <span className="font-medium text-orange-800">Dispute Reason:</span>
                  <p className="text-orange-700 mt-1">{complaint.dispute_reason}</p>
                </div>
              )}

              {/* Dispute Button (only for complaints against user that are pending) */}
              {showDispute && 
               mode === 'against' && 
               complaint.type === 'complaint' && 
               complaint.status === 'pending' && 
               !complaint.disputed && (
                <div className="mt-3">
                  {disputingId === complaint.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={disputeReason}
                        onChange={(e) => setDisputeReason(e.target.value)}
                        placeholder="Explain why you're disputing this complaint (min 10 characters)..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        rows={3}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDispute(complaint.id)}
                          className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm hover:bg-orange-700"
                        >
                          Submit Dispute
                        </button>
                        <button
                          onClick={() => {
                            setDisputingId(null);
                            setDisputeReason('');
                          }}
                          className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDisputingId(complaint.id)}
                      className="text-sm text-orange-600 hover:text-orange-700 font-medium"
                    >
                      Dispute this complaint →
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
