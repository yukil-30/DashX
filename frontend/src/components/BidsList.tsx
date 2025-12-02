
import { BidWithStats } from '../types/api';

interface BidsListProps {
  bids: BidWithStats[];
  onAssignBid?: (bidId: number) => void;
  isManager?: boolean;
}

export default function BidsList({ bids, onAssignBid, isManager = false }: BidsListProps) {
  if (bids.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No bids yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {bids.map((bid) => (
        <div
          key={bid.id}
          className={`p-4 rounded-lg border-2 transition-all ${
            bid.is_lowest_bid
              ? 'border-green-400 bg-green-50'
              : 'border-gray-200 bg-white'
          }`}
        >
          <div className="flex items-start justify-between">
            {/* Bid Info */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-semibold text-gray-900">
                  {bid.delivery_person_email}
                </span>
                {bid.is_lowest_bid && (
                  <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full font-semibold">
                    LOWEST BID
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Bid Amount:</span>
                  <span className="ml-2 font-bold text-lg text-primary-600">
                    {bid.bid_amount_formatted}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Status:</span>
                  <span className={`ml-2 font-medium ${
                    bid.status === 'accepted' ? 'text-green-600' : 
                    bid.status === 'rejected' ? 'text-red-600' : 
                    'text-yellow-600'
                  }`}>
                    {bid.status}
                  </span>
                </div>
              </div>

              {/* Delivery Person Stats */}
              <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                <div className="text-xs font-semibold text-gray-700 mb-2">
                  Delivery Stats
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs">
                  <div>
                    <div className="text-gray-600">Deliveries</div>
                    <div className="font-semibold">{bid.stats.total_deliveries}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Rating</div>
                    <div className="font-semibold flex items-center gap-1">
                      ⭐ {bid.stats.average_rating.toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600">On-Time</div>
                    <div className="font-semibold">{bid.stats.on_time_percentage}%</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Warnings</div>
                    <div className={`font-semibold ${bid.stats.warnings_count > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {bid.stats.warnings_count}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Button */}
            {isManager && bid.status === 'pending' && onAssignBid && (
              <button
                onClick={() => onAssignBid(bid.id)}
                className="btn-primary ml-4"
              >
                Assign
              </button>
            )}
          </div>

          <div className="text-xs text-gray-500 mt-2">
            Submitted: {new Date(bid.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
