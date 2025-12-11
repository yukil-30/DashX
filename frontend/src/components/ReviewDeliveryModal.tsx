import { useState } from 'react';
import { X, Truck, Clock, ThumbsUp, ThumbsDown } from 'lucide-react';
import apiClient from '../lib/api-client';
import toast from 'react-hot-toast';

interface ReviewDeliveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: number;
  deliveryPersonId: number;
  deliveryPersonEmail: string | null;
  onReviewSubmitted: () => void;
}

export default function ReviewDeliveryModal({
  isOpen,
  onClose,
  orderId,
  deliveryPersonId,
  deliveryPersonEmail,
  onReviewSubmitted
}: ReviewDeliveryModalProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [reviewText, setReviewText] = useState('');
  const [onTime, setOnTime] = useState<boolean | null>(null);
  const [feedbackType, setFeedbackType] = useState<'none' | 'compliment' | 'complaint'>('none');
  const [feedbackText, setFeedbackText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (rating === 0) {
      setError('Please select a rating');
      return;
    }

    if (feedbackType !== 'none' && !feedbackText.trim()) {
      setError(`Please provide details for your ${feedbackType}`);
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Submit delivery review
      await apiClient.post('/reviews/delivery', {
        order_id: orderId,
        rating: rating,
        review_text: reviewText.trim() || null,
        on_time: onTime
      });

      // Submit complaint/compliment if selected
      if (feedbackType !== 'none') {
        await apiClient.post('/complaints', {
          about_user_id: deliveryPersonId,
          order_id: orderId,
          type: feedbackType,
          text: feedbackText.trim()
        });
      }

      toast.success(
        feedbackType === 'none' 
          ? 'Delivery review submitted!'
          : `Delivery review and ${feedbackType} submitted!`
      );
      onReviewSubmitted();
      handleClose();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to submit review';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setRating(0);
    setHoverRating(0);
    setReviewText('');
    setOnTime(null);
    setFeedbackType('none');
    setFeedbackText('');
    setError('');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Rate Delivery</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={loading}
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* Delivery Person Info */}
          <div className="mb-6 flex items-center gap-3">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
              <Truck size={24} className="text-primary-600" />
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-900">Delivery Driver</p>
              {deliveryPersonEmail && (
                <p className="text-sm text-gray-600">{deliveryPersonEmail}</p>
              )}
            </div>
          </div>

          {/* Star Rating */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              How was your delivery experience? *
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="text-4xl transition-transform hover:scale-110"
                >
                  {star <= (hoverRating || rating) ? '⭐' : '☆'}
                </button>
              ))}
            </div>
            {rating > 0 && (
              <p className="text-sm text-gray-600 mt-1">
                {rating === 1 && 'Poor'}
                {rating === 2 && 'Fair'}
                {rating === 3 && 'Good'}
                {rating === 4 && 'Very Good'}
                {rating === 5 && 'Excellent'}
              </p>
            )}
          </div>

          {/* On Time Question */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Was your delivery on time?
            </label>
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => setOnTime(true)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  onTime === true 
                    ? 'border-green-500 bg-green-50 text-green-700' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <Clock size={18} />
                Yes, on time
              </button>
              <button
                type="button"
                onClick={() => setOnTime(false)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  onTime === false 
                    ? 'border-red-500 bg-red-50 text-red-700' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <Clock size={18} />
                No, late
              </button>
            </div>
          </div>

          {/* Review Text */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional comments (optional)
            </label>
            <textarea
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder="Share your delivery experience..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
              rows={3}
              maxLength={2000}
            />
          </div>

          {/* Feedback Section */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm font-medium text-gray-700 mb-3">
              Want to leave additional feedback for the delivery driver?
            </p>
            <div className="flex gap-4 mb-4">
              <button
                type="button"
                onClick={() => setFeedbackType(feedbackType === 'compliment' ? 'none' : 'compliment')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
                  feedbackType === 'compliment'
                    ? 'border-green-500 bg-green-50 text-green-700'
                    : 'border-gray-200 hover:border-green-300 text-gray-600'
                }`}
              >
                <ThumbsUp size={20} />
                Compliment
              </button>
              <button
                type="button"
                onClick={() => setFeedbackType(feedbackType === 'complaint' ? 'none' : 'complaint')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
                  feedbackType === 'complaint'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-gray-200 hover:border-red-300 text-gray-600'
                }`}
              >
                <ThumbsDown size={20} />
                Complaint
              </button>
            </div>

            {feedbackType !== 'none' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {feedbackType === 'compliment' 
                    ? 'What did the driver do well?' 
                    : 'What went wrong?'}
                </label>
                <textarea
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder={
                    feedbackType === 'compliment'
                      ? 'e.g., Very friendly, handled food with care...'
                      : 'e.g., Food was cold, driver was rude...'
                  }
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                  rows={3}
                  required
                />
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || rating === 0}
              className="flex-1 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Submitting...' : 'Submit Review'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
