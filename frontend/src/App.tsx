import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CartProvider, useCart } from './contexts/CartContext'
import { WarningsBanner } from './components'

// Pages
import HomePage from './pages/HomePage'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import RegisterManagerPage from './pages/auth/RegisterManagerPage'
import DishesPage from './pages/DishesPage'
import DishDetailPage from './pages/DishDetailPage'
import CartPage from './pages/CartPage'
import ChatPage from './pages/ChatPage'
import ImageSearchPage from './pages/ImageSearchPage'
import ChefDashboard from './pages/chef/ChefDashboard'
import CreateDish from './pages/chef/CreateDish';
import ModifyDish from "./pages/chef/ModifyDish";
import DeliveryDashboard from './pages/delivery/DeliveryDashboard'
import { ManagerOrders } from './pages/manager/ManagerOrders'
import { ManagerOrderDetail } from './pages/manager/ManagerOrderDetail'
import { ManagerComplaints } from './pages/manager/ManagerComplaints'
import { ManagerDashboard } from './pages/manager/ManagerDashboard'
import { ManagerEmployees } from './pages/manager/ManagerEmployees'
import { ManagerDisputes } from './pages/manager/ManagerDisputes'
import { ManagerBidding } from './pages/manager/ManagerBidding'
import { ManagerKB } from './pages/manager/ManagerKB'

// Customer Feature Pages
import CustomerDashboard from './pages/customer/CustomerDashboard'
import OrderHistoryPage from './pages/customer/OrderHistoryPage'
import TransactionsPage from './pages/customer/TransactionsPage'
import ForumPage from './pages/ForumPage'
import ThreadDetailPage from './pages/ThreadDetailPage'
import ChefsListPage from './pages/ChefsListPage'
import ChefProfilePage from './pages/ChefProfilePage'

function Navigation() {
  const { user, logout, warningInfo, dismissWarning } = useAuth();
  const { totalItems } = useCart();

  return (
    <nav className="bg-white shadow-md sticky top-0 z-40 animate-slide-down">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 md:h-20">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-3xl">🍽️</span>
            <span className="text-2xl font-bold text-gray-900">DashX</span>
          </Link>

          {/* Main Navigation */}
          <div className="flex items-center gap-3 md:gap-6">
            <Link to="/dishes" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
              <span className="hidden sm:inline">Menu</span>
              <span className="sm:hidden text-xl">📖</span>
            </Link>
            <Link to="/image-search" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
              <span className="hidden sm:inline">Image Search</span>
              <span className="sm:hidden text-xl">🔍</span>
            </Link>
            <Link to="/chat" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
              <span className="hidden sm:inline">Support</span>
              <span className="sm:hidden text-xl">💬</span>
            </Link>

            {/* Role-specific links */}
            {user?.type === 'manager' && (
              <div className="relative group">
                <button className="text-gray-700 hover:text-primary-600 font-medium flex items-center gap-1">
                  Manager Menu ▾
                </button>
                <div className="absolute top-full left-0 hidden group-hover:block bg-white shadow-lg rounded-lg border py-2 min-w-48 z-50">
                  <Link to="/manager/dashboard" className="block px-4 py-2 hover:bg-gray-100">📊 Dashboard</Link>
                  <Link to="/manager/employees" className="block px-4 py-2 hover:bg-gray-100">👥 Employees</Link>
                  <Link to="/manager/orders" className="block px-4 py-2 hover:bg-gray-100">📋 Orders</Link>
                  <Link to="/manager/disputes" className="block px-4 py-2 hover:bg-gray-100">⚖️ Disputes</Link>
                  <Link to="/manager/bidding" className="block px-4 py-2 hover:bg-gray-100">🎯 Bidding</Link>
                  <Link to="/manager/kb" className="block px-4 py-2 hover:bg-gray-100">📚 KB Moderation</Link>
                  <Link to="/manager/complaints" className="block px-4 py-2 hover:bg-gray-100">📝 Complaints</Link>
                </div>
              </div>
            )}

            {user?.type === 'chef' && (
              <Link to="/chef/dashboard" className="text-gray-700 hover:text-primary-600 font-medium">
                My Dishes
              </Link>
            )}

            {user?.type === 'delivery' && (
              <Link to="/delivery/dashboard" className="text-gray-700 hover:text-primary-600 font-medium">
                Dashboard
              </Link>
            )}

            {/* Customer Navigation */}
            {user?.type === 'customer' && (
              <>
                <Link to="/customer/dashboard" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
                  <span className="hidden sm:inline">My Dashboard</span>
                  <span className="sm:hidden text-xl">📊</span>
                </Link>
                <Link to="/customer/orders" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
                  <span className="hidden sm:inline">My Orders</span>
                  <span className="sm:hidden text-xl">📋</span>
                </Link>
              </>
            )}

            {/* Public Links */}
            <Link to="/chefs" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
              <span className="hidden sm:inline">Chefs</span>
              <span className="sm:hidden text-xl">👨‍🍳</span>
            </Link>
            <Link to="/forum" className="text-gray-700 hover:text-primary-600 font-medium transition-colors duration-200 hover:scale-105">
              <span className="hidden sm:inline">Forum</span>
              <span className="sm:hidden text-xl">💭</span>
            </Link>

            {/* Cart (customers only) */}
            {user?.type === 'customer' && (
              <Link to="/cart" className="relative text-gray-700 hover:text-primary-600 transition-colors">
                <span className="text-2xl">🛒</span>
                {totalItems > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                    {totalItems}
                  </span>
                )}
              </Link>
            )}

            {/* Auth */}
            {user ? (
              <div className="flex items-center gap-4">
                <span className="text-gray-700">
                  {user.email} <span className="text-xs text-gray-500">({user.type})</span>
                </span>
                <button onClick={logout} className="btn-secondary text-sm">
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link to="/auth/login" className="btn-secondary text-sm">
                  Login
                </Link>
                <Link to="/auth/register" className="btn-primary text-sm">
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Warnings Banner */}
      {warningInfo && warningInfo.warnings_count > 0 && (
        <div className="border-t border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
            <WarningsBanner
              warningsCount={warningInfo.warnings_count}
              message={warningInfo.warning_message}
              isNearThreshold={warningInfo.is_near_threshold}
              onDismiss={dismissWarning}
            />
          </div>
        </div>
      )}
    </nav>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<HomePage />} />
      <Route path="/dishes" element={<DishesPage />} />
      <Route path="/dishes/:id" element={<DishDetailPage />} />
      <Route path="/image-search" element={<ImageSearchPage />} />
      <Route path="/chat" element={<ChatPage />} />

      {/* Auth Routes */}
      <Route
        path="/auth/login"
        element={user ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/auth/register"
        element={user ? <Navigate to="/" replace /> : <RegisterPage />}
      />
      <Route
        path="/auth/register-manager"
        element={user ? <Navigate to="/" replace /> : <RegisterManagerPage />}
      />

      {/* Customer Routes */}
      <Route
        path="/cart"
        element={
          user?.type === 'customer' ? <CartPage /> : <Navigate to="/auth/login" replace />
        }
      />
      <Route
        path="/customer/dashboard"
        element={
          user?.type === 'customer' ? <CustomerDashboard /> : <Navigate to="/auth/login" replace />
        }
      />
      <Route
        path="/customer/orders"
        element={
          user?.type === 'customer' ? <OrderHistoryPage /> : <Navigate to="/auth/login" replace />
        }
      />
      <Route
        path="/customer/transactions"
        element={
          user?.type === 'customer' ? <TransactionsPage /> : <Navigate to="/auth/login" replace />
        }
      />

      {/* Public Profile Routes */}
      <Route path="/chefs" element={<ChefsListPage />} />
      <Route path="/chefs/:id" element={<ChefProfilePage />} />
      <Route path="/forum" element={<ForumPage />} />
      <Route path="/forum/:threadId" element={<ThreadDetailPage />} />

      {/* Manager Routes */}
      <Route
        path="/manager/dashboard"
        element={
          user?.type === 'manager' ? <ManagerDashboard /> : <Navigate to="/" replace />
        }
      />
      <Route
        path="/manager/employees"
        element={
          user?.type === 'manager' ? <ManagerEmployees /> : <Navigate to="/" replace />
        }
      />
      <Route
        path="/manager/disputes"
        element={
          user?.type === 'manager' ? <ManagerDisputes /> : <Navigate to="/" replace />
        }
      />
      <Route
        path="/manager/bidding"
        element={
          user?.type === 'manager' ? <ManagerBidding /> : <Navigate to="/" replace />
        }
      />
      <Route
        path="/manager/kb"
        element={
          user?.type === 'manager' ? <ManagerKB /> : <Navigate to="/" replace />
        }
      />
      <Route
        path="/manager/orders"
        element={
          user?.type === 'manager' ? (
            <ManagerOrders />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        path="/manager/orders/:orderId"
        element={
          user?.type === 'manager' ? (
            <ManagerOrderDetail />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        path="/manager/complaints"
        element={
          user?.type === 'manager' ? (
            <ManagerComplaints />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />

      {/* Chef Routes */}
      <Route
        path="/chef/dashboard"
        element={user?.type === 'chef' ? <ChefDashboard /> : <Navigate to="/" replace />}
      />
	<Route
	 	path="/chef/dishes/new"
  		element={user?.type === 'chef' ? <CreateDish /> : <Navigate to="/" replace />}
	/>
	<Route
	 	path="/chef/dishes/:dishId/edit"
  		element={user?.type === 'chef' ? <ModifyDish /> : <Navigate to="/" replace />}
	/>

      {/* Delivery Routes */}
      <Route
        path="/delivery/dashboard"
        element={
          user?.type === 'delivery' ? <DeliveryDashboard /> : <Navigate to="/" replace />
        }
      />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <CartProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
          <div className="min-h-screen flex flex-col bg-gray-50">
            <Navigation />
            <main className="flex-1">
              <AppRoutes />
            </main>
            <footer className="bg-gray-800 text-white py-6 mt-12">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                <p>&copy; 2025 DashX Restaurant. All rights reserved.</p>
              </div>
            </footer>
          </div>
        </CartProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
