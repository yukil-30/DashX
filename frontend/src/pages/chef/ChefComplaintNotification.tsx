import { useState, useEffect } from 'react';
import { X, AlertTriangle, ThumbsUp, ThumbsDown } from 'lucide-react';
import apiClient from '../lib/api-client';
import { useAuth } from '../contexts/AuthContext';

interface Complaint {
  id: number;
  type: 'complaint' | 'compliment';
  description: string;
  filer_email: string | null;
  order_id: number | null;
  status: string;
  created_at: string;
}

interface ComplaintSummary {
  total_complaints: number;
  unresolved_complaints: number;
  total_compliments: number;
  recent_items: Complaint[];
}

export default function ChefComplaintNotification() {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [summary, setSummary] = useState<ComplaintSummary | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (user && user.type === 'chef' && !dismissed) {
      fetchComplaintSummary();
    }
  }, [user, dismissed]);

  const fetchComplaintSummary = async () => {
    try {
      const response = await apiClient.get<ComplaintSummary>('/complaints/my-summary');
      setSummary(response.data);
      
      // Auto-open if there are unresolved complaints
      if (response.data.unresolved_complaints > 0) {
        setIsOpen(true);
      }
    } catch (err) {
      console.error('Failed to fetch complaint summary:', err);
    }
  };

  const handleDismiss = () => {
    setIsOpen(false);
    setDismissed(true);
  };

  if (!user || user.type !== 'chef' || !summary || !isOpen) {
    return null;
  }

  const hasUnresolvedComplaints = summary.unresolved_complaints > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className={`p-6 border-b ${hasUnresolvedComplaints ? 'bg-red-50 border-red-200' : 'bg-blue-50 border-blue-200'}`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {hasUnresolvedComplaints ? (
                <AlertTriangle className="text-red-600" size={32} />
              ) : (
                <ThumbsUp className="text-blue-600" size={32} />
              )}
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {hasUnresolvedComplaints ? 'Attention Required' : 'Feedback Summary'}
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  {hasUnresolvedComplaints 
                    ? 'You have pending complaints that need your attention'
                    : 'Here\'s your recent feedback summary'
                  }
                </p>
              </div>
            </div>
            <button
              onClick={handleDismiss}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="p-6 border-b border-gray-200">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="flex items-center justify-center gap-2 mb-2">
                <ThumbsDown className="text-red-600" size={20} />
                <p className="text-3xl font-bold text-red-600">
                  {summary.total_complaints}
                </p>
              </div>
              <p className="text-sm text-gray-600">Total Complaints</p>
              {summary.unresolved_complaints > 0 && (
                <p className="text-xs text-red-600 font-medium mt-1">
                  {summary.unresolved_complaints} unresolved
                </p>
              )}
            </div>

            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="flex items-center justify-center gap-2 mb-2">
                <ThumbsUp className="text-green-600" size={20} />
                <p className="text-3xl font-bold text-green-600">
                  {summary.total_compliments}
                </p>
              </div>
              <p className="text-sm text-gray-600">Compliments</p>
            </div>

            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-center gap-2 mb-2">
                <span className="text-2xl">⚖️</span>
                <p className="text-3xl font-bold text-blue-600">
                  {summary.total_compliments - summary.total_complaints}
                </p>
              </div>
              <p className="text-sm text-gray-600">Net Score</p>
              <p className="text-xs text-gray-500 mt-1">
                Compliments offset complaints
              </p>
            </div>
          </div>
        </div>

        {/* Recent Items */}
        {summary.recent_items.length > 0 && (
          <div className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Recent Feedback</h3>
            <div className="space-y-3">
              {summary.recent_items.map((item) => (
                <div
                  key={item.id}
                  className={`p-4 rounded-lg border-2 ${
                    item.type === 'complaint'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-green-50 border-green-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {item.type === 'complaint' ? (
                      <ThumbsDown className="text-red-600 flex-shrink-0 mt-1" size={20} />
                    ) : (
                      <ThumbsUp className="text-green-600 flex-shrink-0 mt-1" size={20} />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-semibold ${
                          item.type === 'complaint' ? 'text-red-800' : 'text-green-800'
                        }`}>
                          {item.type === 'complaint' ? 'Complaint' : 'Compliment'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mb-2">
                        {item.description}
                      </p>
                      {item.filer_email && (
                        <p className="text-xs text-gray-500">
                          From: {item.filer_email}
                        </p>
                      )}
                      {item.order_id && (
                        <p className="text-xs text-gray-500">
                          Order #{item.order_id}
                        </p>
                      )}
                      <span className={`inline-block mt-2 px-2 py-1 rounded text-xs font-medium ${
                        item.status === 'pending'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {item.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Warning Info */}
        {hasUnresolvedComplaints && (
          <div className="p-6 bg-yellow-50 border-t border-yellow-200">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-yellow-600 flex-shrink-0" size={20} />
              <div className="text-sm text-yellow-800">
                <p className="font-semibold mb-1">Important Information</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li>Complaints are reviewed by management</li>
                  <li>3 or more complaints may result in demotion</li>
                  <li>Compliments can offset complaints (1:1 ratio)</li>
                  <li>Maintain high dish ratings to avoid performance issues</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="p-6 border-t border-gray-200">
          <button
            onClick={handleDismiss}
            className="w-full btn-primary py-3"
          >
            I Understand
          </button>
        </div>
      </div>
    </div>
  );
}