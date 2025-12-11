import { useCallback, useEffect, useState } from 'react'
import apiClient from '../../lib/api-client'
import { Link } from 'react-router-dom'

interface AccountSummary {
  id: number
  email: string
  type: string
  warnings: number
  is_blacklisted: boolean
  customer_tier?: string
  balance: number
  has_pending_deregister?: boolean
}

interface AttemptItem {
  id: number
  title: string
  message: string
  related_account_id?: number | null
  created_at?: string | null
}

interface ManagerNotificationItem {
  id: number
  notification_type: string
  title: string
  message: string
  related_account_id?: number | null
  created_at?: string | null
}

export function ManagerRegistration() {
  const [accounts, setAccounts] = useState<AccountSummary[]>([])
  const [attempts, setAttempts] = useState<AttemptItem[]>([])
  const [loadingAccounts, setLoadingAccounts] = useState(true)
  const [loadingAttempts, setLoadingAttempts] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionInProgress, setActionInProgress] = useState<number | null>(null)
  const [showBlacklisted, setShowBlacklisted] = useState<boolean>(false)

  const fetchAccounts = useCallback(async () => {
    setLoadingAccounts(true)
    try {
      const res = await apiClient.get<AccountSummary[]>('/manager/accounts', {
        params: { show_blacklisted: showBlacklisted }
      })
      setAccounts(res.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load accounts')
    } finally {
      setLoadingAccounts(false)
    }
  }, [showBlacklisted])

  const approveRegistration = async (id: number) => {
    if (!confirm('Approve this registration?')) return
    setActionInProgress(id)
    try {
      await apiClient.post(`/manager/accounts/${id}/approve`)
      alert('Registration approved')
      await fetchAccounts()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to approve')
    } finally {
      setActionInProgress(null)
    }
  }

  const rejectRegistration = async (id: number) => {
    if (!confirm('Reject this registration? Email will be blacklisted.')) return
    setActionInProgress(id)
    try {
      await apiClient.post(`/manager/accounts/${id}/reject`, { reason: 'Rejected by manager' })
      alert('Registration rejected and blacklisted')
      await fetchAccounts()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to reject')
    } finally {
      setActionInProgress(null)
    }
  }

  const fetchAttempts = useCallback(async () => {
    setLoadingAttempts(true)
    try {
      const res = await apiClient.get<{ attempts: AttemptItem[] }>('/manager/blacklist-attempts')
      setAttempts(res.data.attempts || [])
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load attempts')
    } finally {
      setLoadingAttempts(false)
    }
  }, [])

  useEffect(() => {
    fetchAccounts()
    fetchAttempts()
  }, [fetchAccounts, fetchAttempts])

  const toggleShowBlacklisted = () => {
    setShowBlacklisted((prev: boolean) => !prev)
  }

  const closeAccount = async (id: number) => {
    if (!confirm('Close and deregister this account?')) return
    setActionInProgress(id)
    try {
      await apiClient.post(`/manager/accounts/${id}/close`, { reason: 'Closed by manager' })
      alert('Account closed')
      await fetchAccounts()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to close account')
    } finally {
      setActionInProgress(null)
    }
  }

  const approveDeregisterRequest = async (id: number) => {
    if (!confirm('Approve this deregistration request and close the account?')) return
    setActionInProgress(id)
    try {
      await apiClient.post(`/manager/accounts/${id}/close-deregister`)
      alert('Deregistration request approved and account closed')
      await fetchAccounts()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to approve deregistration')
    } finally {
      setActionInProgress(null)
    }
  }

  const addBlacklist = async (email: string, accountId?: number) => {
    if (!confirm(`Add ${email} to blacklist?`)) return
    setActionInProgress(accountId || 0)
    try {
      await apiClient.post('/manager/blacklist', { email, reason: 'Manager action', original_account_id: accountId })
      alert('Blacklisted')
      await fetchAccounts()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to add blacklist')
    } finally {
      setActionInProgress(null)
    }
  }

  return (
    <div className="manager-registrations max-w-5xl mx-auto py-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Registrations & Accounts</h1>
        <div className="flex gap-2">
          <Link to="/manager/dashboard" className="btn-secondary">← Dashboard</Link>
          <div className="flex items-center gap-2">
            <label className="text-sm flex items-center gap-2">
              <input type="checkbox" checked={showBlacklisted} onChange={toggleShowBlacklisted} />
              <span>Show blacklisted</span>
            </label>
          </div>
        </div>
      </header>

      <section className="mt-6">
        <h2 className="text-lg font-semibold mb-2">Accounts Needing Action</h2>
        <p className="text-sm text-gray-600 mb-4">Pending registrations, deregister requests, blacklisted accounts, and accounts with warnings</p>
        {loadingAccounts ? (
          <p>Loading accounts…</p>
        ) : (
          <div className="mt-4 space-y-3">
            {accounts.map((a) => {
              const isPending = a.customer_tier === 'pending'
              const hasDeregisterRequest = a.has_pending_deregister
              return (
                <div key={a.id} className={`p-4 border rounded ${isPending ? 'bg-yellow-50 border-yellow-200' : hasDeregisterRequest ? 'bg-blue-50 border-blue-200' : a.is_blacklisted ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                      <div className="font-medium flex items-center gap-2">
                        {a.email} <span className="text-sm text-gray-500">({a.type})</span>
                        {isPending && <span className="px-2 py-1 bg-yellow-200 text-yellow-800 text-xs rounded font-normal">PENDING</span>}
                        {hasDeregisterRequest && <span className="px-2 py-1 bg-blue-200 text-blue-800 text-xs rounded font-normal">DEREGISTER REQUEST</span>}
                        {a.is_blacklisted && <span className="px-2 py-1 bg-red-200 text-red-800 text-xs rounded font-normal">BLACKLISTED</span>}
                      </div>
                      <div className="text-sm text-gray-600 mt-1">Warnings: {a.warnings} • Tier: {a.customer_tier ?? '—'} • Balance: ${(a.balance / 100).toFixed(2)}</div>
                    </div>
                    <div className="flex gap-2 flex-wrap justify-end">
                      {isPending && (
                        <>
                          <button
                            onClick={() => approveRegistration(a.id)}
                            disabled={actionInProgress === a.id}
                            className="btn-primary text-sm px-3 py-1"
                          >
                            {actionInProgress === a.id ? '...' : 'Approve'}
                          </button>
                          <button
                            onClick={() => rejectRegistration(a.id)}
                            disabled={actionInProgress === a.id}
                            className="btn-danger text-sm px-3 py-1"
                          >
                            {actionInProgress === a.id ? '...' : 'Reject'}
                          </button>
                        </>
                      )}
                      {hasDeregisterRequest && (
                        <button
                          onClick={() => approveDeregisterRequest(a.id)}
                          disabled={actionInProgress === a.id}
                          className="btn-primary text-sm px-3 py-1"
                        >
                          {actionInProgress === a.id ? '...' : 'Close Account'}
                        </button>
                      )}
                      {!isPending && !hasDeregisterRequest && (
                        <>
                          <button onClick={() => closeAccount(a.id)} disabled={actionInProgress === a.id} className="btn-danger text-sm px-3 py-1">Close</button>
                          {!a.is_blacklisted && (
                            <button onClick={() => addBlacklist(a.email, a.id)} disabled={actionInProgress === a.id} className="btn-secondary text-sm px-3 py-1">Blacklist</button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            {accounts.length === 0 && <div className="text-sm text-gray-500">No accounts needing action.</div>}
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Blocked Registration Attempts</h2>
        {loadingAttempts ? (
          <p>Loading attempts…</p>
        ) : (
          <div className="mt-4 space-y-3">
            {attempts.map((it) => (
              <div key={it.id} className="p-3 border rounded">
                <div className="font-medium">{it.title}</div>
                <div className="text-sm text-gray-700">{it.message}</div>
                <div className="text-xs text-gray-500 mt-1">{it.created_at}</div>
              </div>
            ))}
            {attempts.length === 0 && <div className="text-sm text-gray-500">No blocked attempts found.</div>}
          </div>
        )}
      </section>
    </div>
  )
}

export default ManagerRegistration
