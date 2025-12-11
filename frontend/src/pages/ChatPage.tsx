import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../lib/api-client';
import { ChatQueryRequest, ChatQueryResponse, ChatRateRequest, KBContributionCreateRequest, MyKBContributionsResponse } from '../types/api';
import { RatingStars } from '../components';
import { useAuth } from '../contexts/AuthContext';

interface Message {
  id: number;
  question: string;
  answer: string | null;
  source: 'kb' | 'llm' | 'pending';
  rating: number | null;
  timestamp: Date;
  showRatingPrompt?: boolean;
}

export default function ChatPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'chat' | 'contribute'>('chat');
  const [contributionForm, setContributionForm] = useState({
    question: '',
    answer: '',
    keywords: ''
  });
  const [contributionLoading, setContributionLoading] = useState(false);
  const [contributionSuccess, setContributionSuccess] = useState('');
  const [myContributions, setMyContributions] = useState<MyKBContributionsResponse | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Fetch user's contributions when they switch to contribute tab
  useEffect(() => {
    if (activeTab === 'contribute' && user) {
      fetchMyContributions();
    }
  }, [activeTab, user]);

  const fetchMyContributions = async () => {
    try {
      const response = await apiClient.get<MyKBContributionsResponse>('/chat/kb/contributions/mine');
      setMyContributions(response.data);
    } catch (err) {
      // Silently fail - user might not have any contributions
      console.error('Failed to fetch contributions:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim()) return;

    const question = input.trim();
    setInput('');
    setLoading(true);
    setError('');

    // Add pending message immediately
    const tempId = Date.now();
    const pendingMessage: Message = {
      id: tempId,
      question,
      answer: null,
      source: 'pending',
      rating: null,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, pendingMessage]);

    try {
      const request: ChatQueryRequest = { question };
      const response = await apiClient.post<ChatQueryResponse>('/chat/query', request);
      
      // Update the pending message with the real response
      setMessages((prev) => 
        prev.map(msg => 
          msg.id === tempId 
            ? {
                id: response.data.chat_id,
                question: response.data.question,
                answer: response.data.answer,
                source: response.data.source,
                rating: null,
                timestamp: new Date(),
                // Show rating prompt immediately for KB-sourced answers
                showRatingPrompt: response.data.source === 'kb',
              }
            : msg
        )
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message');
      // Remove the pending message on error
      setMessages((prev) => prev.filter(msg => msg.id !== tempId));
    } finally {
      setLoading(false);
    }
  };

  const handleRate = async (messageId: number, rating: number) => {
    try {
      const request: ChatRateRequest = { rating };
      await apiClient.post(`/chat/${messageId}/rate`, request);
      
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId ? { ...msg, rating, showRatingPrompt: false } : msg
        )
      );
    } catch (err: any) {
      console.error('Failed to rate message:', err);
    }
  };

  const handleContributionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!contributionForm.question.trim() || !contributionForm.answer.trim()) {
      setError('Question and answer are required');
      return;
    }

    setContributionLoading(true);
    setError('');
    setContributionSuccess('');

    try {
      const request: KBContributionCreateRequest = {
        question: contributionForm.question.trim(),
        answer: contributionForm.answer.trim(),
        keywords: contributionForm.keywords.trim() || undefined
      };
      
      await apiClient.post('/chat/kb/contribute', request);
      
      setContributionSuccess('Your contribution has been submitted for review. Thank you!');
      setContributionForm({ question: '', answer: '', keywords: '' });
      
      // Refresh contributions list
      fetchMyContributions();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit contribution');
    } finally {
      setContributionLoading(false);
    }
  };

  const getStatusBadge = (status: 'pending' | 'approved' | 'rejected') => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800'
    };
    const icons = {
      pending: '⏳',
      approved: '✅',
      rejected: '❌'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
        {icons[status]} {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-screen flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Customer Support</h1>
        <p className="text-gray-600">
          Ask us anything! We use AI to help answer your questions quickly.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'chat'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat
        </button>
        {user && (
          <button
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'contribute'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setActiveTab('contribute')}
          >
            📝 Contribute Knowledge
          </button>
        )}
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm flex justify-between items-center">
          {error}
          <button onClick={() => setError('')} className="text-red-600 hover:text-red-800">✕</button>
        </div>
      )}

      {contributionSuccess && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-3 text-green-800 text-sm flex justify-between items-center">
          {contributionSuccess}
          <button onClick={() => setContributionSuccess('')} className="text-green-600 hover:text-green-800">✕</button>
        </div>
      )}

      {/* Chat Tab */}
      {activeTab === 'chat' && (
        <>
          {/* Messages Container */}
          <div
            className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-6 mb-4 space-y-6"
            style={{ minHeight: '400px', maxHeight: '60vh' }}
            data-testid="chat-messages"
          >
            {messages.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-6xl mb-4">💬</div>
                <p className="text-lg">Start a conversation!</p>
                <p className="text-sm mt-2">
                  Ask about menu items, orders, delivery, or anything else.
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className="space-y-3">
                  {/* User Question */}
                  <div className="flex justify-end">
                    <div className="bg-primary-600 text-white rounded-lg px-4 py-3 max-w-[80%]">
                      <p>{message.question}</p>
                    </div>
                  </div>

                  {/* Bot Answer */}
                  {message.answer && (
                  <div className="flex justify-start">
                    <div className="bg-white rounded-lg px-4 py-3 max-w-[80%] shadow-md">
                      <div className="flex items-start gap-2 mb-2">
                        <span className="text-2xl">🤖</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-gray-900">DashX Assistant</span>
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full ${
                                message.source === 'kb'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-blue-100 text-blue-700'
                              }`}
                            >
                              {message.source === 'kb' ? 'Knowledge Base' : 'AI Generated'}
                            </span>
                          </div>
                          <p className="text-gray-700 whitespace-pre-wrap">{message.answer}</p>
                        </div>
                      </div>

                      {/* Rating - Always show for answers, highlight for KB answers */}
                      <div className={`mt-3 pt-3 border-t ${message.showRatingPrompt ? 'border-yellow-200 bg-yellow-50 -mx-4 px-4 -mb-3 pb-3 rounded-b-lg' : 'border-gray-100'}`}>
                        {message.showRatingPrompt && message.source === 'kb' && message.rating === null && (
                          <p className="text-xs text-yellow-700 mb-2 font-medium">
                            ⭐ Please rate this answer to help us improve our knowledge base!
                          </p>
                        )}
                        <p className="text-xs text-gray-600 mb-2">Was this helpful?</p>
                        <div className="flex items-center gap-3">
                          <RatingStars
                            rating={message.rating || 0}
                            size="sm"
                            readonly={message.rating !== null}
                            onChange={(rating) => handleRate(message.id, rating)}
                          />
                          {message.rating === null && (
                            <button
                              onClick={() => handleRate(message.id, 0)}
                              className="text-xs text-red-600 hover:text-red-800 underline"
                              title="Report this answer as incorrect or unhelpful"
                            >
                              🚩 Report
                            </button>
                          )}
                        </div>
                        {message.rating !== null && (
                          <p className="text-xs text-green-600 mt-1">
                            {message.rating === 0 ? 'Reported for review. Thank you!' : 'Thanks for your feedback!'}
                          </p>
                        )}
                      </div>

                      <p className="text-xs text-gray-400 mt-2">
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                  )}
                </div>
              ))
            )}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-white rounded-lg px-4 py-3 shadow-md">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                    <span className="text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question..."
              className="input-field flex-1"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-primary px-8"
            >
              Send
            </button>
          </form>
        </>
      )}

      {/* Contribute Tab */}
      {activeTab === 'contribute' && user && (
        <div className="space-y-8">
          {/* Contribution Form */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              📝 Submit a Knowledge Entry
            </h2>
            <p className="text-gray-600 text-sm mb-6">
              Help improve our support system by contributing answers to common questions.
              Your contribution will be reviewed by our team before being added to the knowledge base.
            </p>

            <form onSubmit={handleContributionSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Question *
                </label>
                <input
                  type="text"
                  value={contributionForm.question}
                  onChange={(e) => setContributionForm(prev => ({ ...prev, question: e.target.value }))}
                  placeholder="e.g., How do I track my order?"
                  className="input-field w-full"
                  minLength={10}
                  maxLength={1000}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Minimum 10 characters</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Answer *
                </label>
                <textarea
                  value={contributionForm.answer}
                  onChange={(e) => setContributionForm(prev => ({ ...prev, answer: e.target.value }))}
                  placeholder="Provide a clear and helpful answer..."
                  className="input-field w-full h-32 resize-none"
                  minLength={20}
                  maxLength={5000}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Minimum 20 characters</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Keywords (optional)
                </label>
                <input
                  type="text"
                  value={contributionForm.keywords}
                  onChange={(e) => setContributionForm(prev => ({ ...prev, keywords: e.target.value }))}
                  placeholder="e.g., track, order, status, delivery"
                  className="input-field w-full"
                  maxLength={500}
                />
                <p className="text-xs text-gray-500 mt-1">Comma-separated keywords to help find this answer</p>
              </div>

              <button
                type="submit"
                disabled={contributionLoading || !contributionForm.question.trim() || !contributionForm.answer.trim()}
                className="btn-primary w-full"
              >
                {contributionLoading ? 'Submitting...' : 'Submit Contribution'}
              </button>
            </form>
          </div>

          {/* My Contributions */}
          {myContributions && myContributions.contributions.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                📋 My Contributions ({myContributions.total})
              </h2>
              
              <div className="space-y-4">
                {myContributions.contributions.map((contribution) => (
                  <div
                    key={contribution.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <p className="font-medium text-gray-900">{contribution.question}</p>
                      {getStatusBadge(contribution.status)}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{contribution.answer}</p>
                    {contribution.rejection_reason && (
                      <p className="text-sm text-red-600 bg-red-50 p-2 rounded">
                        <strong>Rejection reason:</strong> {contribution.rejection_reason}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-2">
                      Submitted: {contribution.created_at ? new Date(contribution.created_at).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Not logged in message for contribute tab */}
      {activeTab === 'contribute' && !user && (
        <div className="text-center py-12 text-gray-500">
          <div className="text-6xl mb-4">🔒</div>
          <p className="text-lg">Please log in to contribute knowledge</p>
          <p className="text-sm mt-2">
            Create an account or sign in to submit knowledge base entries.
          </p>
        </div>
      )}
    </div>
  );
}
