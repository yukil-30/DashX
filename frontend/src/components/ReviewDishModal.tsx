import { useState } from 'react';
import { X, ThumbsUp, ThumbsDown } from 'lucide-react';
import apiClient from '../lib/api-client';
import toast from 'react-hot-toast';

interface ReviewDishModalProps {
  isOpen: boolean;
  onClose: () => void;
  dishId: number;
  dishName: string;
  orderId: number;
  chefId: number | null;
  chefName: string | null;
  onReviewSubmitted: () => void;
}

export default function ReviewDishModal({
  isOpen,
  onClose,
  dishId,
  dishName,
  orderId,
  chefId,
  chefName,
  onReviewSubmitted
}: ReviewDishModalProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [reviewText, setReviewText] = useState('');
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
      // Submit dish review
      await apiClient.post('/reviews/dish', {
        dish_id: dishId,
        order_id: orderId,
        rating: rating,
        review_text: reviewText.trim() || null
      });

      // Submit complaint/compliment if selected
      if (feedbackType !== 'none' && chefId) {
        await apiClient.post('/complaints', {
          about_user_id: chefId,
          order_id: orderId,
          type: feedbackType,
          text: feedbackText.trim()
        });
      }

      toast.success(
        feedbackType === 'none' 
          ? `Review submitted for ${dishName}!`
          : `Review and ${feedbackType} submitted!`
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
          <h2 className="text-2xl font-bold text-gray-900">Rate Dish</h2>
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
          {/* Dish Name */}
          <div className="mb-6">
            <p className="text-lg font-semibold text-gray-900">{dishName}</p>
            {chefName && (
              <p className="text-sm text-gray-600 mt-1">Chef: {chefName}</p>
            )}
            <p className="text-sm text-gray-500">How would you rate this dish?</p>
          </div>

          {/* Star Rating */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="focus:outline-none transition-transform hover:scale-110"
                >
                  <svg
                    className={`w-12 h-12 ${
                      star <= (hoverRating || rating)
                        ? 'text-yellow-400 fill-current'
                        : 'text-gray-300'
                    }`}
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="1"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                    />
                  </svg>
                </button>
              ))}
            </div>
            {rating > 0 && (
              <p className="text-sm text-gray-600">
                {rating} out of 5 stars
              </p>
            )}
          </div>

          {/* Review Text (Optional) */}
          <div className="mb-6">
            <label
              htmlFor="reviewText"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Your Review (Optional)
            </label>
            <textarea
              id="reviewText"
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="Tell us what you thought about this dish..."
              maxLength={500}
            />
            <p className="text-xs text-gray-500 mt-1">
              {reviewText.length}/500 characters
            </p>
          </div>

          {/* Chef Feedback Section */}
          {chefId && (
            <div className="mb-6 border-t pt-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Feedback for Chef {chefName ? `(${chefName})` : ''}
              </label>
              
              {/* Feedback Type Buttons */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <button
                  type="button"
                  onClick={() => setFeedbackType('none')}
                  className={`py-3 px-4 rounded-lg border-2 transition-all ${
                    feedbackType === 'none'
                      ? 'border-gray-400 bg-gray-50 font-semibold'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  No Feedback
                </button>
                
                <button
                  type="button"
                  onClick={() => setFeedbackType('compliment')}
                  className={`py-3 px-4 rounded-lg border-2 transition-all flex items-center justify-center gap-2 ${
                    feedbackType === 'compliment'
                      ? 'border-green-500 bg-green-50 text-green-700 font-semibold'
                      : 'border-gray-200 hover:border-green-300'
                  }`}
                >
                  <ThumbsUp size={18} />
                  Compliment
                </button>
                
                <button
                  type="button"
                  onClick={() => setFeedbackType('complaint')}
                  className={`py-3 px-4 rounded-lg border-2 transition-all flex items-center justify-center gap-2 ${
                    feedbackType === 'complaint'
                      ? 'border-red-500 bg-red-50 text-red-700 font-semibold'
                      : 'border-gray-200 hover:border-red-300'
                  }`}
                >
                  <ThumbsDown size={18} />
                  Complaint
                </button>
              </div>

              {/* Feedback Text Area */}
              {feedbackType !== 'none' && (
                <div className="mt-4">
                  <textarea
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    className={`w-full border rounded-lg px-4 py-3 focus:ring-2 focus:border-transparent resize-none ${
                      feedbackType === 'compliment'
                        ? 'border-green-300 focus:ring-green-500'
                        : 'border-red-300 focus:ring-red-500'
                    }`}
                    rows={4}
                    placeholder={
                      feedbackType === 'compliment'
                        ? 'What did the chef do particularly well?'
                        : 'What issue would you like to report about the chef?'
                    }
                    maxLength={500}
                    required={feedbackType !== 'none'}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {feedbackText.length}/500 characters
                  </p>
                  <p className="text-xs text-gray-600 mt-2">
                    {feedbackType === 'compliment' 
                      ? '✨ Compliments help chefs improve and can offset complaints'
                      : '⚠️ Complaints will be reviewed by management'
                    }
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || rating === 0}
              className="flex-1 px-4 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Submitting...' : 'Submit Review'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}