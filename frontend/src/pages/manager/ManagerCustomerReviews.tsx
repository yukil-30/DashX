import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import { RatingStars } from '../../components';
import './ManagerCustomerReviews.css';

interface CustomerReview {
  id: number;
  order_id: number;
  customer_id: number;
  customer_email: string | null;
  reviewer_id: number;
  reviewer_email: string | null;
  rating: number;
  review_text: string | null;
  was_polite: boolean | null;
  easy_to_find: boolean | null;
  created_at: string | null;
}

interface CustomerReviewsResponse {
  reviews: CustomerReview[];
  total: number;
  offset: number;
  limit: number;
}

export function ManagerCustomerReviews() {
  const [reviews, setReviews] = useState<CustomerReview[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const fetchReviews = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<CustomerReviewsResponse>(
        `/reviews/customer/all?offset=${offset}&limit=${limit}`
      );
      setReviews(response.data.reviews);
      setTotal(response.data.total);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load customer reviews');
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (loading) {
    return (
      <div className="manager-customer-reviews">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading customer reviews...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="manager-customer-reviews">
        <div className="error-container">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
          <button onClick={fetchReviews} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="manager-customer-reviews">
      <header className="reviews-header">
        <div className="header-content">
          <Link to="/manager" className="back-link">← Back to Dashboard</Link>
          <h1>📝 Customer Reviews</h1>
          <p className="subtitle">Reviews from delivery drivers about customers</p>
        </div>
        <div className="header-stats">
          <span className="stat">Total: {total} reviews</span>
        </div>
      </header>

      {reviews.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">📭</span>
          <h3>No Customer Reviews Yet</h3>
          <p>Customer reviews from delivery drivers will appear here.</p>
        </div>
      ) : (
        <>
          <div className="reviews-list">
            {reviews.map((review) => (
              <div key={review.id} className="review-card">
                <div className="review-header">
                  <div className="review-parties">
                    <div className="party customer">
                      <span className="label">Customer</span>
                      <span className="email">{review.customer_email || `ID: ${review.customer_id}`}</span>
                    </div>
                    <span className="arrow">←</span>
                    <div className="party reviewer">
                      <span className="label">Reviewed by</span>
                      <span className="email">{review.reviewer_email || `ID: ${review.reviewer_id}`}</span>
                    </div>
                  </div>
                  <div className="review-meta">
                    <span className="order-id">Order #{review.order_id}</span>
                    <span className="date">
                      {review.created_at ? new Date(review.created_at).toLocaleDateString() : 'Unknown'}
                    </span>
                  </div>
                </div>

                <div className="review-body">
                  <div className="rating-section">
                    <RatingStars rating={review.rating} />
                    <span className="rating-number">{review.rating}/5</span>
                  </div>

                  {review.review_text && (
                    <p className="review-text">{review.review_text}</p>
                  )}

                  <div className="review-flags">
                    {review.was_polite !== null && (
                      <span className={`flag ${review.was_polite ? 'positive' : 'negative'}`}>
                        {review.was_polite ? '✓ Polite' : '✗ Not polite'}
                      </span>
                    )}
                    {review.easy_to_find !== null && (
                      <span className={`flag ${review.easy_to_find ? 'positive' : 'negative'}`}>
                        {review.easy_to_find ? '✓ Easy to find' : '✗ Hard to find'}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="pagination-btn"
              >
                ← Previous
              </button>
              <span className="page-info">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="pagination-btn"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ManagerCustomerReviews;
