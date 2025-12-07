import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/api-client';
import { ForumThread } from '../types/api';

export default function ThreadDetailPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [thread, setThread] = useState<ForumThread | null>(null);
  const [loading, setLoading] = useState(true);
  const [newReply, setNewReply] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (threadId) {
      fetchThread();
    }
  }, [threadId]);

  const fetchThread = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<ForumThread>(`/forum/threads/${threadId}`);
      setThread(response.data);
    } catch (err: any) {
      toast.error('Thread not found');
      navigate('/forum');
    } finally {
      setLoading(false);
    }
  };

  const submitReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReply.trim()) {
      toast.error('Please enter a message');
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.post(`/forum/threads/${threadId}/posts`, {
        body: newReply.trim(),
      });
      toast.success('Reply posted!');
      setNewReply('');
      fetchThread();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to post reply');
    } finally {
      setSubmitting(false);
    }
  };

  const deleteThread = async () => {
    if (!confirm('Are you sure you want to delete this thread?')) return;

    try {
      await apiClient.delete(`/forum/threads/${threadId}`);
      toast.success('Thread deleted');
      navigate('/forum');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete thread');
    }
  };

  const deletePost = async (postId: number) => {
    if (!confirm('Are you sure you want to delete this post?')) return;

    try {
      await apiClient.delete(`/forum/posts/${postId}`);
      toast.success('Post deleted');
      fetchThread();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete post');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!thread) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600">Thread not found</p>
        <Link to="/forum" className="btn-primary mt-4 inline-block">
          Back to Forum
        </Link>
      </div>
    );
  }

  const isCreator = thread.created_by_id === user?.ID;
  const isManager = user?.type === 'manager';
  const canDelete = isCreator || isManager;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/forum" className="text-primary-600 hover:underline">
          ← Back to Forum
        </Link>
      </div>

      {/* Thread Header */}
      <div className="bg-white rounded-xl shadow-md p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{thread.topic}</h1>
            <p className="text-gray-500 mt-2">
              Started by {thread.created_by_email || 'Anonymous'}
              {thread.created_at && (
                <span> • {new Date(thread.created_at).toLocaleString()}</span>
              )}
            </p>
          </div>
          {canDelete && (
            <button
              onClick={deleteThread}
              className="text-red-600 hover:text-red-700 text-sm"
            >
              Delete Thread
            </button>
          )}
        </div>
      </div>

      {/* Posts */}
      <div className="space-y-4 mb-8">
        {thread.posts.map((post, index) => {
          const canDeletePost = post.posterID === user?.ID || isManager;
          
          return (
            <div
              key={post.id}
              className={`bg-white rounded-xl shadow-md p-6 ${
                index === 0 ? 'border-l-4 border-primary-500' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                    <span className="text-primary-600 font-medium">
                      {(post.posterID || 0).toString().slice(-2)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      User #{post.posterID}
                    </p>
                    {post.datetime && (
                      <p className="text-sm text-gray-500">
                        {new Date(post.datetime).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {index === 0 && (
                    <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs rounded-full">
                      Original Post
                    </span>
                  )}
                  {canDeletePost && index > 0 && (
                    <button
                      onClick={() => deletePost(post.id)}
                      className="text-red-600 hover:text-red-700 text-sm"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>

              {post.title && (
                <h3 className="font-semibold text-lg text-gray-900 mb-2">
                  {post.title}
                </h3>
              )}
              <p className="text-gray-700 whitespace-pre-wrap">{post.body}</p>
            </div>
          );
        })}
      </div>

      {/* Reply Form */}
      {user ? (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-xl font-semibold mb-4">Add a Reply</h3>
          <form onSubmit={submitReply}>
            <textarea
              value={newReply}
              onChange={(e) => setNewReply(e.target.value)}
              className="input-field resize-none mb-4"
              rows={4}
              placeholder="Write your reply..."
              required
            />
            <button
              type="submit"
              disabled={submitting}
              className="btn-primary"
            >
              {submitting ? 'Posting...' : 'Post Reply'}
            </button>
          </form>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-xl p-6 text-center">
          <p className="text-gray-600 mb-4">Sign in to join the discussion</p>
          <Link to="/auth/login" className="btn-primary">
            Sign In
          </Link>
        </div>
      )}
    </div>
  );
}
