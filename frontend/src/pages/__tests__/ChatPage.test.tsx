import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPage from '../../pages/ChatPage';
import apiClient from '../../lib/api-client';

// Mock the API client
vi.mock('../../lib/api-client');

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chat interface', () => {
    render(<ChatPage />);
    expect(screen.getByText('Customer Support Chat')).toBeDefined();
    expect(screen.getByPlaceholderText('Type your question...')).toBeDefined();
    expect(screen.getByText('Send')).toBeDefined();
  });

  it('displays empty state message initially', () => {
    render(<ChatPage />);
    expect(screen.getByText('Start a conversation!')).toBeDefined();
    expect(screen.getByText(/Ask about menu items/)).toBeDefined();
  });

  it('sends a message when form is submitted', async () => {
    const mockResponse = {
      data: {
        chat_id: 1,
        question: 'What are your hours?',
        answer: 'We are open from 9 AM to 10 PM daily.',
        source: 'kb',
        confidence: 0.9,
      },
    };

    (apiClient.post as any).mockResolvedValueOnce(mockResponse);

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...');
    const sendButton = screen.getByText('Send');

    await userEvent.type(input, 'What are your hours?');
    await userEvent.click(sendButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/chat/query', {
        question: 'What are your hours?',
      });
    });
  });

  it('displays user message and bot response', async () => {
    const mockResponse = {
      data: {
        chat_id: 1,
        question: 'What dishes do you have?',
        answer: 'We have a variety of dishes including pasta, pizza, and salads.',
        source: 'llm',
        confidence: null,
      },
    };

    (apiClient.post as any).mockResolvedValueOnce(mockResponse);

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...');
    
    await userEvent.type(input, 'What dishes do you have?');
    await userEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText('What dishes do you have?')).toBeDefined();
      expect(screen.getByText('We have a variety of dishes including pasta, pizza, and salads.')).toBeDefined();
    });
  });

  it('shows loading state while sending message', async () => {
    const mockResponse = {
      data: {
        chat_id: 1,
        question: 'Test question',
        answer: 'Test answer',
        source: 'kb',
        confidence: 0.8,
      },
    };

    let resolvePromise: any;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    
    (apiClient.post as any).mockReturnValueOnce(promise);

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...');
    await userEvent.type(input, 'Test question');
    await userEvent.click(screen.getByText('Send'));

    // Should show loading state
    expect(screen.getByText('Thinking...')).toBeDefined();

    // Resolve the promise
    resolvePromise(mockResponse);

    await waitFor(() => {
      expect(screen.queryByText('Thinking...')).toBeNull();
    });
  });

  it('displays source badge correctly', async () => {
    const kbResponse = {
      data: {
        chat_id: 1,
        question: 'KB question',
        answer: 'KB answer',
        source: 'kb',
        confidence: 0.9,
      },
    };

    (apiClient.post as any).mockResolvedValueOnce(kbResponse);

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...');
    await userEvent.type(input, 'KB question');
    await userEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText('Knowledge Base')).toBeDefined();
    });
  });

  it('allows rating a message', async () => {
    const queryResponse = {
      data: {
        chat_id: 1,
        question: 'Test',
        answer: 'Test answer',
        source: 'kb',
        confidence: 0.9,
      },
    };

    const rateResponse = { data: { message: 'Rating submitted' } };

    (apiClient.post as any)
      .mockResolvedValueOnce(queryResponse)
      .mockResolvedValueOnce(rateResponse);

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...');
    await userEvent.type(input, 'Test');
    await userEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText('Was this helpful?')).toBeDefined();
    });

    // Click on a star (this is simplified - actual implementation may vary)
    const stars = screen.getAllByRole('button');
    const ratingButton = stars.find(btn => btn.getAttribute('aria-label')?.includes('Rate'));
    if (ratingButton) {
      await userEvent.click(ratingButton);
    }
  });

  it('displays error message when API call fails', async () => {
    (apiClient.post as any).mockRejectedValueOnce({
      response: { data: { detail: 'Network error' } },
    });

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...');
    await userEvent.type(input, 'Test question');
    await userEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText(/Network error|Failed to send message/)).toBeDefined();
    });
  });

  it('clears input after sending message', async () => {
    const mockResponse = {
      data: {
        chat_id: 1,
        question: 'Test',
        answer: 'Answer',
        source: 'kb',
        confidence: 0.9,
      },
    };

    (apiClient.post as any).mockResolvedValueOnce(mockResponse);

    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText('Type your question...') as HTMLInputElement;
    await userEvent.type(input, 'Test');
    
    expect(input.value).toBe('Test');
    
    await userEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(input.value).toBe('');
    });
  });
});
