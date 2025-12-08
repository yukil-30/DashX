import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import apiClient from '../../lib/api-client';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../../lib/api-client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

// Test component to consume AuthContext
const TestComponent = () => {
  const { login, user } = useAuth();
  
  const handleLogin = () => {
    login({ email: 'test@example.com', password: 'password' });
  };

  return (
    <div>
      <button onClick={handleLogin}>Login</button>
      {user && <div data-testid="user-email">{user.email}</div>}
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('login calls correct endpoints', async () => {
    // Mock responses
    (apiClient.post as any).mockResolvedValue({
      data: {
        access_token: 'fake-token',
        token_type: 'bearer',
        expires_in: 3600,
      },
    });

    (apiClient.get as any).mockResolvedValue({
      data: {
        user: {
          ID: 1,
          email: 'test@example.com',
          type: 'customer',
          balance: 0,
          warnings: 0,
          wage: null,
          restaurantID: null,
        },
      },
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Click login
    screen.getByText('Login').click();

    // Verify /auth/login call
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password',
      });
    });

    // Verify /auth/me call (was /account/profile)
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/auth/me', expect.objectContaining({
        headers: { Authorization: 'Bearer fake-token' },
      }));
    });

    // Verify user is set
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    });
  });
});
