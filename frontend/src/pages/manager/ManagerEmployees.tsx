import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import './ManagerEmployees.css';

interface Employee {
  id: number;
  email: string;
  type: string;
  wage: number | null;
  warnings: number;
  times_demoted: number;
  is_fired: boolean;
  restaurant_id: number | null;
  total_complaints: number;
  total_compliments: number;
  average_rating: number | null;
  total_reviews: number;
}

interface EmployeeListResponse {
  employees: Employee[];
  total: number;
  chefs_count: number;
  delivery_count: number;
}

interface ActionResult {
  message: string;
  success: boolean;
}

export function ManagerEmployees() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [chefsCount, setChefsCount] = useState(0);
  const [deliveryCount, setDeliveryCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [includeFired, setIncludeFired] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState<ActionResult | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 100 };
      if (roleFilter) params.role_filter = roleFilter;
      params.include_fired = includeFired;
      
      const response = await apiClient.get<EmployeeListResponse>('/manager/employees', { params });
      setEmployees(response.data.employees);
      setTotal(response.data.total);
      setChefsCount(response.data.chefs_count);
      setDeliveryCount(response.data.delivery_count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load employees');
    } finally {
      setLoading(false);
    }
  }, [roleFilter, includeFired]);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const handleAction = async (employeeId: number, action: string, amount?: number) => {
    setActionLoading(true);
    setActionResult(null);
    try {
      const body: any = { action };
      if (amount) body.amount_cents = amount;
      
      const response = await apiClient.post(`/manager/employees/${employeeId}/action`, body);
      setActionResult({ message: response.data.message, success: true });
      fetchEmployees();
      setSelectedEmployee(null);
    } catch (err: any) {
      setActionResult({
        message: err.response?.data?.detail || 'Action failed',
        success: false
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleEvaluateAll = async () => {
    setActionLoading(true);
    try {
      const response = await apiClient.post('/manager/employees/evaluate-all');
      setActionResult({
        message: `Evaluated ${response.data.results.length} employees`,
        success: true
      });
      fetchEmployees();
    } catch (err: any) {
      setActionResult({
        message: err.response?.data?.detail || 'Evaluation failed',
        success: false
      });
    } finally {
      setActionLoading(false);
    }
  };

  const formatCurrency = (cents: number | null) => {
    if (cents === null) return 'N/A';
    return `$${(cents / 100).toFixed(2)}/hr`;
  };

  const getRatingBadge = (rating: number | null) => {
    if (rating === null) return <span className="rating-badge none">No ratings</span>;
    if (rating >= 4) return <span className="rating-badge high">⭐ {rating.toFixed(1)}</span>;
    if (rating >= 2) return <span className="rating-badge medium">⭐ {rating.toFixed(1)}</span>;
    return <span className="rating-badge low">⚠️ {rating.toFixed(1)}</span>;
  };

  const getStatusBadge = (employee: Employee) => {
    if (employee.is_fired) return <span className="status-badge fired">Fired</span>;
    if (employee.times_demoted >= 1) return <span className="status-badge at-risk">At Risk ({employee.times_demoted}x demoted)</span>;
    return <span className="status-badge active">Active</span>;
  };

  return (
    <div className="manager-employees">
      <header className="page-header">
        <div className="header-left">
          <Link to="/manager/dashboard" className="back-link">← Dashboard</Link>
          <h1>👥 Employee Management</h1>
        </div>
        <div className="header-stats">
          <span className="stat">👨‍🍳 {chefsCount} Chefs</span>
          <span className="stat">🛵 {deliveryCount} Delivery</span>
          <span className="stat">Total: {total}</span>
        </div>
      </header>

      <div className="controls">
        <div className="filters">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Roles</option>
            <option value="chef">Chefs</option>
            <option value="delivery">Delivery</option>
          </select>
          
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeFired}
              onChange={(e) => setIncludeFired(e.target.checked)}
            />
            Include Fired
          </label>
        </div>
        
        <div className="actions">
          <button
            onClick={handleEvaluateAll}
            className="btn-secondary"
            disabled={actionLoading}
          >
            📋 Evaluate All
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            ➕ Create Employee
          </button>
          <button onClick={fetchEmployees} className="btn-refresh">
            🔄
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {actionResult && (
        <div className={`result-banner ${actionResult.success ? 'success' : 'error'}`}>
          {actionResult.message}
          <button onClick={() => setActionResult(null)}>✕</button>
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading employees...</p>
        </div>
      ) : (
        <div className="employees-table-container">
          <table className="employees-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Role</th>
                <th>Wage</th>
                <th>Rating</th>
                <th>Reviews</th>
                <th>Complaints</th>
                <th>Compliments</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {employees.length === 0 ? (
                <tr>
                  <td colSpan={9} className="empty-row">
                    No employees found.
                  </td>
                </tr>
              ) : (
                employees.map((emp) => (
                  <tr key={emp.id} className={emp.is_fired ? 'fired-row' : ''}>
                    <td>
                      <div className="employee-info">
                        <span className="employee-email">{emp.email}</span>
                        <span className="employee-id">ID: {emp.id}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`role-badge ${emp.type}`}>
                        {emp.type === 'chef' ? '👨‍🍳' : '🛵'} {emp.type}
                      </span>
                    </td>
                    <td>{formatCurrency(emp.wage)}</td>
                    <td>{getRatingBadge(emp.average_rating)}</td>
                    <td>{emp.total_reviews}</td>
                    <td>
                      <span className={`count-badge ${emp.total_complaints >= 3 ? 'danger' : ''}`}>
                        {emp.total_complaints}
                      </span>
                    </td>
                    <td>
                      <span className="count-badge success">{emp.total_compliments}</span>
                    </td>
                    <td>{getStatusBadge(emp)}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          onClick={() => setSelectedEmployee(emp)}
                          className="btn-action"
                        >
                          ⚙️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Action Modal */}
      {selectedEmployee && (
        <div className="modal-overlay" onClick={() => setSelectedEmployee(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Actions for {selectedEmployee.email}</h3>
            <p className="employee-summary">
              {selectedEmployee.type === 'chef' ? '👨‍🍳' : '🛵'} {selectedEmployee.type} | 
              Wage: {formatCurrency(selectedEmployee.wage)} | 
              Rating: {selectedEmployee.average_rating?.toFixed(1) || 'N/A'} | 
              Demotions: {selectedEmployee.times_demoted}
            </p>

            <div className="action-grid">
              {!selectedEmployee.is_fired && (
                <>
                  <button
                    onClick={() => handleAction(selectedEmployee.id, 'promote')}
                    className="action-btn promote"
                    disabled={actionLoading}
                  >
                    📈 Promote (+10% wage)
                  </button>
                  <button
                    onClick={() => handleAction(selectedEmployee.id, 'demote')}
                    className="action-btn demote"
                    disabled={actionLoading}
                  >
                    📉 Demote (-10% wage)
                  </button>
                  <button
                    onClick={() => {
                      const amount = prompt('Enter bonus amount in cents:');
                      if (amount) handleAction(selectedEmployee.id, 'bonus', parseInt(amount));
                    }}
                    className="action-btn bonus"
                    disabled={actionLoading}
                  >
                    💰 Give Bonus
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Are you sure you want to fire this employee?')) {
                        handleAction(selectedEmployee.id, 'fire');
                      }
                    }}
                    className="action-btn fire"
                    disabled={actionLoading}
                  >
                    🔥 Fire
                  </button>
                </>
              )}
              {selectedEmployee.is_fired && (
                <button
                  onClick={() => handleAction(selectedEmployee.id, 'promote')}
                  className="action-btn promote"
                  disabled={actionLoading}
                >
                  ♻️ Re-hire (Promote)
                </button>
              )}
            </div>

            <button
              onClick={() => setSelectedEmployee(null)}
              className="close-btn"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Create Employee Modal */}
      {showCreateModal && (
        <CreateEmployeeModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchEmployees();
          }}
        />
      )}
    </div>
  );
}

interface CreateEmployeeModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

function CreateEmployeeModal({ onClose, onSuccess }: CreateEmployeeModalProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'chef' | 'delivery'>('chef');
  const [wage, setWage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await apiClient.post('/manager/employees', {
        email,
        password,
        role,
        wage_cents: wage ? parseInt(wage) : null
      });
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create employee');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content create-modal" onClick={(e) => e.stopPropagation()}>
        <h3>➕ Create New Employee</h3>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="employee@example.com"
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Min 8 characters"
            />
          </div>

          <div className="form-group">
            <label>Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value as 'chef' | 'delivery')}>
              <option value="chef">👨‍🍳 Chef</option>
              <option value="delivery">🛵 Delivery</option>
            </select>
          </div>

          <div className="form-group">
            <label>Hourly Wage (cents)</label>
            <input
              type="number"
              value={wage}
              onChange={(e) => setWage(e.target.value)}
              placeholder="e.g., 1500 for $15/hr"
            />
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="form-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Employee'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ManagerEmployees;
