import React, { useState } from 'react';

interface ManagerAssignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (memo: string) => void;
  bidAmount: string;
  lowestBidAmount: string;
  deliveryPersonEmail: string;
  isLowestBid: boolean;
}

export default function ManagerAssignModal({
  isOpen,
  onClose,
  onConfirm,
  bidAmount,
  lowestBidAmount,
  deliveryPersonEmail,
  isLowestBid,
}: ManagerAssignModalProps) {
  const [memo, setMemo] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // If not lowest bid, memo is required
    if (!isLowestBid && !memo.trim()) {
      alert('Memo is required when not assigning the lowest bid');
      return;
    }
    
    onConfirm(memo);
    setMemo('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-slide-up">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Assign Delivery
        </h2>

        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-600 mb-2">Delivery Person:</div>
          <div className="font-semibold text-gray-900">{deliveryPersonEmail}</div>
          
          <div className="text-sm text-gray-600 mt-3 mb-2">Bid Amount:</div>
          <div className="font-bold text-xl text-primary-600">{bidAmount}</div>
          
          {!isLowestBid && (
            <div className="mt-3 p-2 bg-yellow-50 border border-yellow-300 rounded text-sm">
              <span className="font-semibold text-yellow-800">⚠️ Note:</span>
              <span className="text-yellow-700 ml-1">
                This is not the lowest bid. Lowest bid: {lowestBidAmount}
              </span>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          {!isLowestBid && (
            <div className="mb-4">
              <label htmlFor="memo" className="block text-sm font-medium text-gray-700 mb-2">
                Memo (required for non-lowest bid) <span className="text-red-500">*</span>
              </label>
              <textarea
                id="memo"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                className="input-field resize-none"
                rows={4}
                placeholder="Explain why you're not choosing the lowest bid..."
                required={!isLowestBid}
              />
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
            >
              Confirm Assignment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
