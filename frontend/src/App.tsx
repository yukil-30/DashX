import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import './App.css'
import { ManagerOrders } from './pages/manager/ManagerOrders'
import { ManagerOrderDetail } from './pages/manager/ManagerOrderDetail'

interface HealthStatus {
  status: string
  version: string
  database: string
  llm_stub: string
}

interface LoginFormData {
  email: string
  password: string
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [userType, setUserType] = useState<string | null>(localStorage.getItem('userType'))
  const [loginForm, setLoginForm] = useState<LoginFormData>({ email: '', password: '' })
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState(false)

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch(`${apiUrl}/health`)
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data = await response.json()
        setHealth(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch health status')
        console.error('Health check failed:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 30000)
    return () => clearInterval(interval)
  }, [apiUrl])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginLoading(true)
    setLoginError(null)

    try {
      const response = await fetch(`${apiUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Login failed')
      }

      const data = await response.json()
      setToken(data.access_token)
      localStorage.setItem('token', data.access_token)

      // Fetch user profile to get type
      const profileRes = await fetch(`${apiUrl}/account/profile`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      if (profileRes.ok) {
        const profile = await profileRes.json()
        setUserType(profile.user.type)
        localStorage.setItem('userType', profile.user.type)
      }
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoginLoading(false)
    }
  }

  const handleLogout = () => {
    setToken(null)
    setUserType(null)
    localStorage.removeItem('token')
    localStorage.removeItem('userType')
  }

  const HomePage = () => (
    <>
      <section className="status-section">
        <h2>System Status</h2>
        {loading ? (
          <div className="loading">Loading...</div>
        ) : error ? (
          <div className="error">
            <p>⚠️ Error connecting to backend</p>
            <p className="error-detail">{error}</p>
            <p className="error-hint">Make sure the backend is running at {apiUrl}</p>
          </div>
        ) : health ? (
          <div className="status-grid">
            <div className="status-card">
              <span className="status-label">API Status</span>
              <span className={`status-value ${health.status === 'ok' ? 'status-ok' : 'status-error'}`}>
                {health.status === 'ok' ? '✅ Online' : '❌ Offline'}
              </span>
            </div>
            <div className="status-card">
              <span className="status-label">Version</span>
              <span className="status-value">{health.version}</span>
            </div>
            <div className="status-card">
              <span className="status-label">Database</span>
              <span className={`status-value ${health.database === 'connected' ? 'status-ok' : 'status-warning'}`}>
                {health.database}
              </span>
            </div>
            <div className="status-card">
              <span className="status-label">AI Service</span>
              <span className={`status-value ${health.llm_stub === 'connected' ? 'status-ok' : 'status-warning'}`}>
                {health.llm_stub}
              </span>
            </div>
          </div>
        ) : null}
      </section>

      {!token ? (
        <section className="login-section">
          <h2>Login</h2>
          <form onSubmit={handleLogin} className="login-form">
            <input
              type="email"
              placeholder="Email"
              value={loginForm.email}
              onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              required
            />
            <button type="submit" disabled={loginLoading}>
              {loginLoading ? 'Logging in...' : 'Login'}
            </button>
            {loginError && <p className="login-error">{loginError}</p>}
          </form>
        </section>
      ) : (
        <section className="user-section">
          <h2>Welcome!</h2>
          <p>You are logged in as: <strong>{userType}</strong></p>
          {userType === 'manager' && (
            <div className="manager-links">
              <Link to="/manager/orders" className="nav-link">📋 Manage Orders & Bids</Link>
            </div>
          )}
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </section>
      )}

      <section className="features-section">
        <h2>Features</h2>
        <ul className="features-list">
          <li>📋 Delivery bidding system with manager assignment</li>
          <li>⚡ Real-time bid comparison with lowest bid highlighting</li>
          <li>📊 Delivery person scoreboard (ratings, on-time %)</li>
          <li>💬 Memo requirement for non-lowest bid assignments</li>
        </ul>
      </section>
    </>
  )

  return (
    <Router>
      <div className="app">
        <header className="header">
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <h1>🍽️ DashX Restaurant</h1>
          </Link>
          <p className="subtitle">Your intelligent dining companion</p>
        </header>

        <main className="main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route
              path="/manager/orders"
              element={
                token && userType === 'manager' ? (
                  <ManagerOrders token={token} />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/manager/orders/:orderId"
              element={
                token && userType === 'manager' ? (
                  <ManagerOrderDetail token={token} />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
          </Routes>
        </main>

        <footer className="footer">
          <p>DashX Restaurant &copy; 2025</p>
        </footer>
      </div>
    </Router>
  )
}

export default App
