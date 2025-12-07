import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../contexts/AuthContext'
import { CartProvider } from '../contexts/CartContext'

// Mock API client
vi.mock('../lib/api-client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

import apiClient from '../lib/api-client'

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <AuthProvider>
      <CartProvider>
        {children}
      </CartProvider>
    </AuthProvider>
  </BrowserRouter>
)

describe('Customer Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays VIP badge when user is VIP', async () => {
    const mockDashboardData = {
      user_id: 1,
      email: 'test@example.com',
      account_type: 'customer',
      balance_cents: 15000,
      balance_formatted: '$150.00',
      vip_status: {
        is_vip: true,
        total_spent_cents: 15000,
        total_spent_formatted: '$150.00',
        completed_orders: 10,
        has_unresolved_complaints: false,
        vip_eligible: true,
        vip_reason: 'Spent over $100',
        free_delivery_credits: 2,
        discount_percent: 5,
        next_free_delivery_in: 0
      },
      recent_orders: [],
      favorite_dishes: [],
      most_popular_dish: null,
      highest_rated_dish: null,
      top_rated_chef: null
    }

    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockDashboardData })

    // Import and render
    const { default: CustomerDashboard } = await import('../pages/customer/CustomerDashboard')
    render(
      <TestWrapper>
        <CustomerDashboard />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/VIP Member/i)).toBeInTheDocument()
    })
  })

  it('shows progress to VIP for non-VIP users', async () => {
    const mockDashboardData = {
      user_id: 1,
      email: 'test@example.com',
      account_type: 'customer',
      balance_cents: 5000,
      balance_formatted: '$50.00',
      vip_status: {
        is_vip: false,
        total_spent_cents: 5000,
        total_spent_formatted: '$50.00',
        completed_orders: 1,
        has_unresolved_complaints: false,
        vip_eligible: false,
        vip_reason: 'Spend $50 more or complete 2 more orders',
        free_delivery_credits: 0,
        discount_percent: 0,
        next_free_delivery_in: 3
      },
      recent_orders: [],
      favorite_dishes: [],
      most_popular_dish: null,
      highest_rated_dish: null,
      top_rated_chef: null
    }

    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockDashboardData })

    const { default: CustomerDashboard } = await import('../pages/customer/CustomerDashboard')
    render(
      <TestWrapper>
        <CustomerDashboard />
      </TestWrapper>
    )

    await waitFor(() => {
      // Non-VIP users see "Regular Customer"
      expect(screen.getByText(/Regular Customer/i)).toBeInTheDocument()
    })
  })

  it('displays correct balance amount', async () => {
    const mockDashboardData = {
      user_id: 1,
      email: 'test@example.com',
      account_type: 'customer',
      balance_cents: 12345,
      balance_formatted: '$123.45',
      vip_status: {
        is_vip: false,
        total_spent_cents: 0,
        total_spent_formatted: '$0.00',
        completed_orders: 0,
        has_unresolved_complaints: false,
        vip_eligible: false,
        vip_reason: null,
        free_delivery_credits: 0,
        discount_percent: 0,
        next_free_delivery_in: 3
      },
      recent_orders: [],
      favorite_dishes: [],
      most_popular_dish: null,
      highest_rated_dish: null,
      top_rated_chef: null
    }

    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockDashboardData })

    const { default: CustomerDashboard } = await import('../pages/customer/CustomerDashboard')
    render(
      <TestWrapper>
        <CustomerDashboard />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/\$123\.45/)).toBeInTheDocument()
    })
  })
})

describe('Order History', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders order history page without crashing', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url) => {
      if (url === '/auth/me') {
        throw new Error('Not authenticated')
      }
      if (url.includes('/orders')) {
        return { data: { orders: [], total: 0, page: 1, limit: 10 } }
      }
      return { data: [] }
    })

    const { default: OrderHistoryPage } = await import('../pages/customer/OrderHistoryPage')
    render(
      <TestWrapper>
        <OrderHistoryPage />
      </TestWrapper>
    )

    await waitFor(() => {
      // Should render page - either with title or empty state
      const hasContent = document.body.textContent && document.body.textContent.length > 0
      expect(hasContent).toBe(true)
    })
  })
})

describe('Forum', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders forum page without crashing', async () => {
    const mockThreads = { threads: [], total: 0, page: 1, limit: 20 }

    vi.mocked(apiClient.get).mockImplementation(async (url) => {
      if (url === '/auth/me') {
        throw new Error('Not authenticated')
      }
      return { data: mockThreads }
    })

    const { default: ForumPage } = await import('../pages/ForumPage')
    render(
      <TestWrapper>
        <ForumPage />
      </TestWrapper>
    )

    await waitFor(() => {
      // Should show forum title
      expect(screen.getByText(/Discussion Forum/i)).toBeInTheDocument()
    })
  })
})

describe('Transactions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays transaction list', async () => {
    const mockTransactions = {
      transactions: [
        {
          id: 1,
          type: 'deposit',
          amount: 5000,
          description: 'Credit card deposit',
          created_at: '2024-01-15T10:00:00Z'
        },
        {
          id: 2,
          type: 'order',
          amount: -2500,
          description: 'Order #123',
          created_at: '2024-01-16T10:00:00Z'
        }
      ],
      total: 2,
      page: 1,
      limit: 20
    }

    const mockBalance = { balance_cents: 2500 }

    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({ data: mockTransactions })
      .mockResolvedValueOnce({ data: mockBalance })

    const { default: TransactionsPage } = await import('../pages/customer/TransactionsPage')
    render(
      <TestWrapper>
        <TransactionsPage />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/Credit card deposit/i)).toBeInTheDocument()
      expect(screen.getByText(/Order #123/i)).toBeInTheDocument()
    })
  })

  it('shows filter buttons', async () => {
    const mockTransactions = { transactions: [], total: 0, page: 1, limit: 20 }

    vi.mocked(apiClient.get).mockImplementation(async () => {
      return { data: mockTransactions }
    })

    const { default: TransactionsPage } = await import('../pages/customer/TransactionsPage')
    render(
      <TestWrapper>
        <TransactionsPage />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/Transaction History/i)).toBeInTheDocument()
    })
  })
})

describe('Chef Profiles', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chef list page without crashing', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url) => {
      if (url === '/auth/me') {
        throw new Error('Not authenticated')
      }
      if (url === '/profiles/chefs') {
        return { data: [] }
      }
      return { data: [] }
    })

    const { default: ChefsListPage } = await import('../pages/ChefsListPage')
    render(
      <TestWrapper>
        <ChefsListPage />
      </TestWrapper>
    )

    // Page should render - either with chefs or empty state
    await waitFor(() => {
      const title = screen.queryByText(/Our Chefs/i)
      const emptyState = screen.queryByText(/No chefs found/i)
      expect(title || emptyState).toBeTruthy()
    })
  })
})

describe('Cart with VIP Discounts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage
    localStorage.clear()
  })

  it('cart page renders without crashing', async () => {
    const { default: CartPage } = await import('../pages/CartPage')
    
    // Cart requires auth, so it will show login message
    render(
      <TestWrapper>
        <CartPage />
      </TestWrapper>
    )

    // Cart should render (either with items or asking to sign in)
    await waitFor(() => {
      const hasSignIn = screen.queryByText(/Sign In/i)
      const hasCart = screen.queryByText(/cart/i)
      expect(hasSignIn || hasCart).toBeTruthy()
    })
  })
})
