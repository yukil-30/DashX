import { useState } from 'react';
import { X, Star, User } from 'lucide-react';
import toast from 'react-hot-toast';
import apiClient from '../lib/api-client';

interface ReviewCustomerModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: number;
  customerId: number;
  customerEmail: string | null;
  onReviewSubmitted: () => void;
}

export default function ReviewCustomerModal({
  isOpen,
  onClose,
  orderId,
  customerId,
  customerEmail,
  onReviewSubmitted
}: ReviewCustomerModalProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [reviewText, setReviewText] = useState('');
  const [wasPolite, setWasPolite] = useState<boolean | null>(null);
  const [easyToFind, setEasyToFind] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (rating === 0) {
      toast.error('Please select a rating');
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.post('/reviews/customer', {
        order_id: orderId,
        rating,
        review_text: reviewText || null,
        was_polite: wasPolite,
        easy_to_find: easyToFind
      });
      
      toast.success('Review submitted successfully!');
      onReviewSubmitted();
      onClose();
      
      // Reset form
      setRating(0);
      setReviewText('');
      setWasPolite(null);
      setEasyToFind(null);
    } catch (err: any) {
      console.error('Failed to submit review:', err);
      toast.error(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">Review Customer</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-4 space-y-6">
          {/* Customer Info */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <User size={24} className="text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {customerEmail || `Customer #${customerId}`}
              </p>
              <p className="text-sm text-gray-500">Order #{orderId}</p>
            </div>
          </div>

          {/* Star Rating */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Overall Rating *
            </label>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="p-1 transition-transform hover:scale-110"
                >
                  <Star
                    size={32}
                    className={`${
                      star <= (hoverRating || rating)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-300'
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>

          {/* Quick Feedback Options */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Was the customer polite?
              </label>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setWasPolite(true)}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                    wasPolite === true
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  👍 Yes
                </button>
                <button
                  type="button"
                  onClick={() => setWasPolite(false)}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                    wasPolite === false
                      ? 'border-red-500 bg-red-50 text-red-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  👎 No
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Was the address easy to find?
              </label>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setEasyToFind(true)}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                    easyToFind === true
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  ✓ Easy
                </button>
                <button
                  type="button"
                  onClick={() => setEasyToFind(false)}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                    easyToFind === false
                      ? 'border-red-500 bg-red-50 text-red-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  ✗ Difficult
                </button>
              </div>
            </div>
          </div>

          {/* Review Text */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Comments (optional)
            </label>
            <textarea
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder="Share your experience with this customer..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows={3}
              maxLength={2000}
            />
          </div>

          {/* Submit Button */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || rating === 0}
              className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? 'Submitting...' : 'Submit Review'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
