import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { ComplaintsList, WarningsBanner } from '../../components';

export default function ChefComplaintsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'filed' | 'against'>('against');
  const [showWarning, setShowWarning] = useState(true);

  const warnings = user?.warnings || 0;
  const isNearThreshold = warnings >= 2;

  const getWarningMessage = () => {
    if (warnings >= 2) {
      return `You have ${warnings} complaints. This may affect your employment status.`;
    }
    return null;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Warnings Banner */}
      {showWarning && warnings > 0 && (
        <WarningsBanner
          warningsCount={warnings}
          message={getWarningMessage()}
          isNearThreshold={isNearThreshold}
          onDismiss={() => setShowWarning(false)}
        />
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-2">
          <Link to="/chef/dashboard" className="text-primary-600 hover:text-primary-700">
            ← Back to Dashboard
          </Link>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Complaints & Compliments</h1>
        <p className="text-gray-600 mt-2">
          View complaints and compliments about your dishes and service.
          You can dispute complaints if you believe they are unfair.
        </p>
      </div>

      {/* Status Stats */}
      <div className="bg-white rounded-xl shadow-md p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Status</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Role</p>
            <p className="text-xl font-bold">Chef</p>
          </div>
          <div className={`rounded-lg p-4 ${warnings > 0 ? 'bg-yellow-50' : 'bg-green-50'}`}>
            <p className="text-sm text-gray-600">Complaints</p>
            <p className={`text-xl font-bold ${warnings > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
              {warnings}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">Status</p>
            <p className={`text-xl font-bold ${warnings === 0 ? 'text-green-600' : 'text-yellow-600'}`}>
              {warnings === 0 ? 'Good Standing' : 'Under Review'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('against')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'against'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            About You
          </button>
          <button
            onClick={() => setActiveTab('filed')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'filed'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Filed by You
          </button>
        </nav>
      </div>

      {/* Complaints List */}
      <ComplaintsList mode={activeTab} showDispute={activeTab === 'against'} />

      {/* Help Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">How it Works</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Customers can file complaints about dishes or service quality</li>
          <li>• You can dispute complaints if you believe they are unfair</li>
          <li>• Disputed complaints are reviewed by managers</li>
          <li>• Compliments can cancel out complaints</li>
          <li>• 3 unresolved complaints or average dish rating below 2 may result in demotion</li>
          <li>• Two demotions may result in termination</li>
        </ul>
      </div>
    </div>
  );
}
