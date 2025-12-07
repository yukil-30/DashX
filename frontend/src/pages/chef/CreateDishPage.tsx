import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiClient from '../../lib/api-client';

export default function CreateDishPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cost, setCost] = useState('');
  const [picture, setPicture] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!name.trim()) {
      setError('Dish name is required');
      return;
    }

    const costCents = Math.round(parseFloat(cost) * 100);
    if (isNaN(costCents) || costCents <= 0) {
      setError('Please enter a valid price');
      return;
    }

    setLoading(true);

    try {
      await apiClient.post('/dishes', {
        name: name.trim(),
        description: description.trim() || null,
        cost: costCents,
        picture: picture.trim() || null,
      });

      toast.success('Dish created successfully!');
      navigate('/chef/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create dish');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <Link to="/chef/dashboard" className="text-gray-600 hover:text-gray-900">
          ← Back to Dashboard
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 mt-4">Create New Dish</h1>
        <p className="text-gray-600 mt-2">Add a new dish to your menu</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-md p-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
            {error}
          </div>
        )}

        <div className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              Dish Name *
            </label>
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
              placeholder="e.g., Spaghetti Carbonara"
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="input-field"
              placeholder="Describe your dish..."
            />
          </div>

          <div>
            <label htmlFor="cost" className="block text-sm font-medium text-gray-700 mb-2">
              Price ($) *
            </label>
            <input
              id="cost"
              type="number"
              step="0.01"
              min="0.01"
              required
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              className="input-field"
              placeholder="12.99"
            />
          </div>

          <div>
            <label htmlFor="picture" className="block text-sm font-medium text-gray-700 mb-2">
              Image URL (optional)
            </label>
            <input
              id="picture"
              type="url"
              value={picture}
              onChange={(e) => setPicture(e.target.value)}
              className="input-field"
              placeholder="https://example.com/image.jpg"
            />
            <p className="text-sm text-gray-500 mt-1">
              Enter a URL to an image of your dish
            </p>
          </div>
        </div>

        <div className="mt-8 flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex-1"
          >
            {loading ? 'Creating...' : 'Create Dish'}
          </button>
          <Link to="/chef/dashboard" className="btn-secondary">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
