import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../lib/api-client';
import { ChatQueryRequest, ChatQueryResponse, ChatRateRequest } from '../types/api';
import { RatingStars } from '../components';

interface Message {
  id: number;
  question: string;
  answer: string;
  source: 'kb' | 'llm';
  rating: number | null;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim()) return;

    const question = input.trim();
    setInput('');
    setLoading(true);
    setError('');

    try {
      const request: ChatQueryRequest = { question };
      const response = await apiClient.post<ChatQueryResponse>('/chat/query', request);
      
      const newMessage: Message = {
        id: response.data.chat_id,
        question: response.data.question,
        answer: response.data.answer,
        source: response.data.source,
        rating: null,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, newMessage]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message');
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
          msg.id === messageId ? { ...msg, rating } : msg
        )
      );
    } catch (err: any) {
      console.error('Failed to rate message:', err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-screen flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Customer Support Chat</h1>
        <p className="text-gray-600">
          Ask us anything! We use AI to help answer your questions quickly.
        </p>
      </div>

      {/* Messages Container */}
      <div
        className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-6 mb-4 space-y-6"
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

                  {/* Rating */}
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <p className="text-xs text-gray-600 mb-2">Was this helpful?</p>
                    <RatingStars
                      rating={message.rating || 0}
                      size="sm"
                      readonly={message.rating !== null}
                      onChange={(rating) => handleRate(message.id, rating)}
                    />
                    {message.rating !== null && (
                      <p className="text-xs text-green-600 mt-1">Thanks for your feedback!</p>
                    )}
                  </div>

                  <p className="text-xs text-gray-400 mt-2">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
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

      {/* Error */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm">
          {error}
        </div>
      )}

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
    </div>
  );
}
