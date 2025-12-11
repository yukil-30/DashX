import { useState } from 'react';
import toast from 'react-hot-toast';
import apiClient from '../lib/api-client';
import { ComplaintCreateRequest, Complaint } from '../types/api';

interface ComplaintFormProps {
  orderId: number;
  targetUserId: number;
  targetType: 'chef' | 'delivery' | 'customer';
  targetEmail: string;
  onSuccess?: (complaint: Complaint) => void;
  onCancel?: () => void;
}

export default function ComplaintForm({
  orderId,
  targetUserId,
  targetType,
  targetEmail,
  onSuccess,
  onCancel,
}: ComplaintFormProps) {
  const [type, setType] = useState<'complaint' | 'compliment'>('complaint');
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      toast.error('Please enter a description');
      return;
    }
    if (text.length < 10) {
      toast.error('Description must be at least 10 characters');
      return;
    }

    setSubmitting(true);
    try {
      const request: ComplaintCreateRequest = {
        about_user_id: targetUserId,
        order_id: orderId,
        type,
        text: text.trim(),
        target_type: targetType,
      };
      const response = await apiClient.post<Complaint>('/complaints', request);
      toast.success(`${type === 'complaint' ? 'Complaint' : 'Compliment'} submitted successfully`);
      setText('');
      if (onSuccess) {
        onSuccess(response.data);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        File Feedback for {targetEmail}
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Order #{orderId} • {targetType.charAt(0).toUpperCase() + targetType.slice(1)}
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Type Selection */}
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="type"
              value="complaint"
              checked={type === 'complaint'}
              onChange={() => setType('complaint')}
              className="w-4 h-4 text-red-600"
            />
            <span className={type === 'complaint' ? 'text-red-600 font-medium' : 'text-gray-600'}>
              ⚠️ Complaint
            </span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="type"
              value="compliment"
              checked={type === 'compliment'}
              onChange={() => setType('compliment')}
              className="w-4 h-4 text-green-600"
            />
            <span className={type === 'compliment' ? 'text-green-600 font-medium' : 'text-gray-600'}>
              ⭐ Compliment
            </span>
          </label>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {type === 'complaint' ? 'What went wrong?' : 'What did they do well?'}
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder={type === 'complaint' 
              ? 'Please describe the issue in detail...'
              : 'Share what you appreciated...'
            }
            maxLength={2000}
          />
          <p className="text-xs text-gray-500 mt-1">{text.length}/2000 characters</p>
        </div>

        {/* Warning for complaints */}
        {type === 'complaint' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
            ⚠️ Filing false complaints may result in warnings on your account.
            Please ensure your complaint is legitimate.
          </div>
        )}

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
              type === 'complaint'
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-green-600 hover:bg-green-700 text-white'
            } disabled:opacity-50`}
          >
            {submitting ? 'Submitting...' : `Submit ${type === 'complaint' ? 'Complaint' : 'Compliment'}`}
          </button>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
