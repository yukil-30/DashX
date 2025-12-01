import { useState, useEffect } from 'react'
import './App.css'

interface HealthStatus {
  status: string
  version: string
  database: string
  llm_stub: string
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
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
    // Refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="app">
      <header className="header">
        <h1>🍽️ Local AI-enabled Restaurant</h1>
        <p className="subtitle">Your intelligent dining companion</p>
      </header>

      <main className="main">
        <section className="status-section">
          <h2>System Status</h2>
          {loading ? (
            <div className="loading">Loading...</div>
          ) : error ? (
            <div className="error">
              <p>⚠️ Error connecting to backend</p>
              <p className="error-detail">{error}</p>
              <p className="error-hint">Make sure the backend is running at {import.meta.env.VITE_API_URL || 'http://localhost:8000'}</p>
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

        <section className="features-section">
          <h2>Features (Coming Soon)</h2>
          <ul className="features-list">
            <li>📋 AI-powered menu recommendations</li>
            <li>🛒 Smart ordering system</li>
            <li>💬 Natural language order processing</li>
            <li>📊 Real-time kitchen dashboard</li>
          </ul>
        </section>
      </main>

      <footer className="footer">
        <p>Local AI-enabled Restaurant &copy; 2025</p>
      </footer>
    </div>
  )
}

export default App
