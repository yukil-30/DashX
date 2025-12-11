import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/api-client';
import { ForumThread, ThreadListResponse } from '../types/api';

export default function ForumPage() {
  const { user } = useAuth();
  const [threads, setThreads] = useState<ForumThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showNewThread, setShowNewThread] = useState(false);
  const [newTopic, setNewTopic] = useState('');
  const [newBody, setNewBody] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchThreads();
  }, [page]);

  const fetchThreads = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<ThreadListResponse>(
        `/forum/threads?page=${page}&per_page=20`
      );
      setThreads(response.data.threads);
      setTotal(response.data.total);
    } catch (err: any) {
      toast.error('Failed to load forum');
    } finally {
      setLoading(false);
    }
  };

  const createThread = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopic.trim() || !newBody.trim()) {
      toast.error('Please enter a topic and message');
      return;
    }

    setCreating(true);
    try {
      await apiClient.post('/forum/threads', {
        topic: newTopic.trim(),
        body: newBody.trim(),
      });
      toast.success('Thread created!');
      setNewTopic('');
      setNewBody('');
      setShowNewThread(false);
      fetchThreads();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create thread');
    } finally {
      setCreating(false);
    }
  };

  if (loading && threads.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Discussion Forum</h1>
          <p className="text-gray-600 mt-2">
            Discuss dishes, chefs, delivery, and more
          </p>
        </div>
        {user && (
          <button
            onClick={() => setShowNewThread(true)}
            className="btn-primary"
          >
            + New Thread
          </button>
        )}
      </div>

      {/* New Thread Form */}
      {showNewThread && (
        <div className="bg-white rounded-xl shadow-md p-6 mb-8">
          <h3 className="text-xl font-semibold mb-4">Create New Thread</h3>
          <form onSubmit={createThread}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Topic
              </label>
              <input
                type="text"
                value={newTopic}
                onChange={(e) => setNewTopic(e.target.value)}
                className="input-field"
                placeholder="What's your topic?"
                maxLength={255}
                required
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Message
              </label>
              <textarea
                value={newBody}
                onChange={(e) => setNewBody(e.target.value)}
                className="input-field resize-none"
                rows={4}
                placeholder="Share your thoughts..."
                required
              />
            </div>
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => setShowNewThread(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating}
                className="btn-primary"
              >
                {creating ? 'Creating...' : 'Create Thread'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Thread List */}
      {threads.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl shadow-md">
          <div className="text-6xl mb-4">💬</div>
          <p className="text-gray-600 text-xl mb-4">No discussions yet</p>
          {user ? (
            <button
              onClick={() => setShowNewThread(true)}
              className="btn-primary"
            >
              Start the first thread
            </button>
          ) : (
            <Link to="/auth/login" className="btn-primary">
              Sign in to start a discussion
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {threads.map((thread) => (
            <Link
              key={thread.id}
              to={`/forum/${thread.id}`}
              className="block bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 hover:text-primary-600">
                    {thread.topic}
                  </h3>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <span>
                      by {thread.created_by_email || 'Anonymous'}
                    </span>
                    {thread.created_at && (
                      <span>
                        {new Date(thread.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-gray-500">
                  <span className="text-2xl">💬</span>
                  <span className="font-medium">{thread.posts_count}</span>
                </div>
              </div>
            </Link>
          ))}
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
          <span className="py-2 px-4">
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

      {/* Info Card */}
      <div className="mt-8 bg-blue-50 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-blue-800 mb-2">
          Forum Guidelines
        </h3>
        <ul className="text-blue-700 space-y-1">
          <li>• Be respectful to other members</li>
          <li>• Discuss dishes, chefs, delivery experiences</li>
          <li>• Share tips and recommendations</li>
          <li>• Report any issues to management</li>
        </ul>
      </div>
    </div>
  );
}
