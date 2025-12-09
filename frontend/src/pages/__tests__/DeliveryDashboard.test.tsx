import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import DeliveryDashboard from '../delivery/DeliveryDashboard';
import apiClient from '../../lib/api-client';

// Mock the API client
vi.mock('../../lib/api-client');
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockAvailableOrders = {
  orders: [
    {
      id: 1,
      customer_email: 'customer@test.com',
      delivery_address: '123 Test St',
      subtotal_cents: 2000,
      delivery_fee_cents: 500,
      total_cents: 2500,
      created_at: '2024-01-01T12:00:00Z',
      bidding_closes_at: '2024-01-01T13:00:00Z',
      items: [{ dish_id: 1, dish_name: 'Pizza', quantity: 2, unit_price_cents: 1000 }],
      items_count: 2,
      bid_count: 3,
      lowest_bid_cents: 300,
      has_user_bid: false,
      user_bid_id: null,
      user_bid_amount: null,
      note: 'Leave at door',
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

const mockMyBids = {
  bids: [
    {
      bid_id: 10,
      order_id: 2,
      bid_amount_cents: 450,
      estimated_minutes: 30,
      created_at: '2024-01-01T11:00:00Z',
      bid_status: 'pending',
      is_lowest: true,
      order_status: 'paid',
      order_delivery_address: '456 Another St',
      order_total_cents: 3000,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

const mockAssignedOrders = {
  orders: [
    {
      id: 3,
      customer_email: 'vip@test.com',
      delivery_address: '789 VIP Lane',
      total_cents: 5000,
      delivery_fee_cents: 600,
      estimated_minutes: 25,
      status: 'assigned',
      created_at: '2024-01-01T10:00:00Z',
      items: [
        { dish_id: 5, dish_name: 'Steak', quantity: 1 },
        { dish_id: 6, dish_name: 'Wine', quantity: 2 },
      ],
      items_count: 3,
      note: 'VIP customer',
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

const mockStats = {
  account_id: 10,
  email: 'delivery@test.com',
  average_rating: 4.7,
  total_reviews: 25,
  total_deliveries: 50,
  on_time_deliveries: 45,
  on_time_percentage: 90.0,
  avg_delivery_minutes: 28,
  warnings: 0,
  total_bids: 100,
  pending_deliveries: 1,
  recent_reviews: [],
};

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('DeliveryDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock responses
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.includes('available-orders')) {
        return Promise.resolve({ data: mockAvailableOrders });
      }
      if (url.includes('my-bids')) {
        return Promise.resolve({ data: mockMyBids });
      }
      if (url.includes('assigned')) {
        return Promise.resolve({ data: mockAssignedOrders });
      }
      if (url.includes('stats')) {
        return Promise.resolve({ data: mockStats });
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });
  });

  describe('Initial Rendering', () => {
    it('renders the dashboard header', async () => {
      renderWithRouter(<DeliveryDashboard />);
      
      expect(screen.getByText('Delivery Dashboard')).toBeDefined();
    });

    it('shows loading state initially', () => {
      renderWithRouter(<DeliveryDashboard />);
      
      // Should show loading spinner initially
      expect(document.querySelector('.animate-spin')).toBeDefined();
    });

    it('displays stats summary after loading', async () => {
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('50')).toBeDefined(); // Total Deliveries
        expect(screen.getByText('4.7 ⭐')).toBeDefined(); // Rating
        expect(screen.getByText('90%')).toBeDefined(); // On Time
      });
    });

    it('displays tab navigation', async () => {
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/Available Orders/)).toBeDefined();
        expect(screen.getByText(/My Bids/)).toBeDefined();
        expect(screen.getByText(/Assigned/)).toBeDefined();
      });
    });
  });

  describe('Available Orders Tab', () => {
    it('displays available orders', async () => {
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Order #1')).toBeDefined();
        expect(screen.getByText('123 Test St')).toBeDefined();
        expect(screen.getByText('3 bids')).toBeDefined();
      });
    });

    it('shows lowest bid amount', async () => {
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/\$3.00/)).toBeDefined();
      });
    });

    it('shows place bid button when user has not bid', async () => {
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Place Bid')).toBeDefined();
      });
    });

    it('opens bid modal when clicking Place Bid', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Place Bid')).toBeDefined();
      });
      
      await user.click(screen.getByText('Place Bid'));
      
      await waitFor(() => {
        expect(screen.getByText('Place Bid for Order #1')).toBeDefined();
        expect(screen.getByText('Your Bid Amount ($)')).toBeDefined();
      });
    });
  });

  describe('Bid Submission', () => {
    it('submits bid successfully', async () => {
      const user = userEvent.setup();
      
      (apiClient.post as any).mockResolvedValueOnce({
        data: {
          id: 100,
          deliveryPersonID: 10,
          orderID: 1,
          bidAmount: 350,
          estimated_minutes: 25,
          is_lowest: true,
        },
      });
      
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Place Bid')).toBeDefined();
      });
      
      await user.click(screen.getByText('Place Bid'));
      
      // Fill in the form
      const amountInput = screen.getByPlaceholderText('5.00');
      const minutesInput = screen.getByPlaceholderText('30');
      
      await user.clear(amountInput);
      await user.type(amountInput, '3.50');
      await user.clear(minutesInput);
      await user.type(minutesInput, '25');
      
      // There are two Place Bid buttons - one on the card and one in the modal
      const modalButtons = screen.getAllByText('Place Bid');
      const submitButton = modalButtons[modalButtons.length - 1];
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/delivery/orders/1/bid', {
          price_cents: 350,
          estimated_minutes: 25,
        });
      });
    });

    it('closes modal on cancel', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Place Bid')).toBeDefined();
      });
      
      await user.click(screen.getByText('Place Bid'));
      
      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeDefined();
      });
      
      await user.click(screen.getByText('Cancel'));
      
      await waitFor(() => {
        expect(screen.queryByText('Place Bid for Order #1')).toBeNull();
      });
    });
  });

  describe('My Bids Tab', () => {
    it('switches to bids tab when clicked', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/My Bids/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/My Bids/));
      
      await waitFor(() => {
        expect(screen.getByText('Order #2')).toBeDefined();
        expect(screen.getByText(/\$4.50/)).toBeDefined();
      });
    });

    it('shows bid status badge', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/My Bids/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/My Bids/));
      
      await waitFor(() => {
        // Look for the badge element specifically (has rounded-full class)
        const badges = screen.getAllByText('Pending');
        const statusBadge = badges.find(el => el.classList.contains('rounded-full'));
        expect(statusBadge).toBeDefined();
      });
    });

    it('shows lowest bid indicator', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/My Bids/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/My Bids/));
      
      await waitFor(() => {
        expect(screen.getByText('✓ Lowest bid')).toBeDefined();
      });
    });
  });

  describe('Assigned Orders Tab', () => {
    it('switches to assigned tab when clicked', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/Assigned/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/Assigned/));
      
      await waitFor(() => {
        expect(screen.getByText('Order #3')).toBeDefined();
        expect(screen.getByText('789 VIP Lane')).toBeDefined();
      });
    });

    it('shows mark as delivered button', async () => {
      const user = userEvent.setup();
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/Assigned/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/Assigned/));
      
      await waitFor(() => {
        expect(screen.getByText('✓ Mark as Delivered')).toBeDefined();
      });
    });

    it('marks order as delivered successfully', async () => {
      const user = userEvent.setup();
      
      (apiClient.post as any).mockResolvedValueOnce({
        data: {
          message: 'Order marked as delivered',
          order_id: 3,
          delivered_at: '2024-01-01T14:00:00Z',
          status: 'delivered',
        },
      });
      
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/Assigned/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/Assigned/));
      
      await waitFor(() => {
        expect(screen.getByText('✓ Mark as Delivered')).toBeDefined();
      });
      
      await user.click(screen.getByText('✓ Mark as Delivered'));
      
      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/delivery/orders/3/mark-delivered');
      });
    });
  });

  describe('Empty States', () => {
    it('shows empty message when no available orders', async () => {
      (apiClient.get as any).mockImplementation((url: string) => {
        if (url.includes('available-orders')) {
          return Promise.resolve({ data: { orders: [], total: 0 } });
        }
        if (url.includes('my-bids')) {
          return Promise.resolve({ data: mockMyBids });
        }
        if (url.includes('assigned')) {
          return Promise.resolve({ data: mockAssignedOrders });
        }
        if (url.includes('stats')) {
          return Promise.resolve({ data: mockStats });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });
      
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('No orders available for bidding at the moment.')).toBeDefined();
      });
    });

    it('shows empty message when no bids placed', async () => {
      const user = userEvent.setup();
      
      (apiClient.get as any).mockImplementation((url: string) => {
        if (url.includes('available-orders')) {
          return Promise.resolve({ data: mockAvailableOrders });
        }
        if (url.includes('my-bids')) {
          return Promise.resolve({ data: { bids: [], total: 0 } });
        }
        if (url.includes('assigned')) {
          return Promise.resolve({ data: mockAssignedOrders });
        }
        if (url.includes('stats')) {
          return Promise.resolve({ data: mockStats });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });
      
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/My Bids/)).toBeDefined();
      });
      
      await user.click(screen.getByText(/My Bids/));
      
      await waitFor(() => {
        expect(screen.getByText("You haven't placed any bids yet.")).toBeDefined();
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API error gracefully', async () => {
      const toast = await import('react-hot-toast');
      
      (apiClient.get as any).mockRejectedValueOnce(new Error('Network error'));
      
      renderWithRouter(<DeliveryDashboard />);
      
      await waitFor(() => {
        expect(toast.default.error).toHaveBeenCalledWith('Failed to load dashboard data');
      });
    });
  });
});
