import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../../lib/api-client';
import { TransactionItem, TransactionListResponse } from '../../types/api';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    fetchTransactions();
  }, [page, filter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      let url = `/account/transactions?page=${page}&limit=20`;
      if (filter) {
        url += `&transaction_type=${filter}`;
      }
      const response = await apiClient.get<TransactionListResponse>(url);
      setTransactions(response.data?.transactions || []);
      setTotal(response.data?.total || 0);
    } catch (err: any) {
      toast.error('Failed to load transactions');
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'deposit':
        return '💰';
      case 'withdrawal':
        return '💸';
      case 'order_payment':
        return '🛒';
      case 'refund':
        return '↩️';
      case 'order_refund':
        return '↩️';
      default:
        return '📝';
    }
  };

  const getTypeColor = (_type: string, amount: number) => {
    if (amount > 0) {
      return 'text-green-600';
    } else {
      return 'text-red-600';
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Transaction History</h1>
          <p className="text-gray-600 mt-2">View all your account transactions</p>
        </div>
        <Link to="/dashboard" className="text-primary-600 hover:underline">
          ← Back to Dashboard
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-md p-4 mb-6">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setFilter('')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === '' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('deposit')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'deposit' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            💰 Deposits
          </button>
          <button
            onClick={() => setFilter('withdrawal')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'withdrawal' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            💸 Withdrawals
          </button>
          <button
            onClick={() => setFilter('order_payment')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'order_payment' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🛒 Orders
          </button>
          <button
            onClick={() => setFilter('refund')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'refund' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            ↩️ Refunds
          </button>
        </div>
      </div>

      {/* Transactions List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : !transactions || transactions.length === 0 ? (
        <div className="bg-white rounded-xl shadow-md p-12 text-center">
          <div className="text-6xl mb-4">📝</div>
          <p className="text-gray-600 text-xl">No transactions found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left py-3 px-4 text-gray-600 font-medium">Date</th>
                  <th className="text-left py-3 px-4 text-gray-600 font-medium">Type</th>
                  <th className="text-left py-3 px-4 text-gray-600 font-medium">Description</th>
                  <th className="text-right py-3 px-4 text-gray-600 font-medium">Amount</th>
                  <th className="text-right py-3 px-4 text-gray-600 font-medium">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-gray-50">
                    <td className="py-4 px-4 text-gray-500 text-sm">
                      {tx.created_at ? new Date(tx.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="py-4 px-4">
                      <span className="inline-flex items-center gap-1">
                        <span>{getTypeIcon(tx.transaction_type || '')}</span>
                        <span className="capitalize text-gray-700">
                          {(tx.transaction_type || '').replace(/_/g, ' ')}
                        </span>
                      </span>
                    </td>
                    <td className="py-4 px-4 text-gray-600">
                      {tx.description || '-'}
                      {tx.reference_id && (
                        <span className="text-gray-400 text-sm ml-2">
                          (#{tx.reference_id})
                        </span>
                      )}
                    </td>
                    <td className={`py-4 px-4 text-right font-medium ${getTypeColor(tx.transaction_type, tx.amount_cents)}`}>
                      {tx.amount_cents >= 0 ? '+' : ''}${(tx.amount_cents / 100).toFixed(2)}
                    </td>
                    <td className="py-4 px-4 text-right text-gray-600">
                      ${(tx.balance_after / 100).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary disabled:opacity-50"
          >
            ← Previous
          </button>
          <span className="py-2 px-4 text-gray-600">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            className="btn-secondary disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
