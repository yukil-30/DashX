import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useCart } from '../contexts/CartContext';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/api-client';
import { CreateOrderRequest } from '../types/api';

export default function CartPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { items, updateQuantity, removeFromCart, clearCart, totalCost } = useCart();
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (items.length === 0) {
      setError('Cart is empty');
      return;
    }

    if (!deliveryAddress.trim()) {
      setError('Please enter a delivery address');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const orderRequest: CreateOrderRequest = {
        items: items.map((item) => ({
          dish_id: item.dish.id,
          quantity: item.quantity,
        })),
        delivery_address: deliveryAddress.trim(),
      };

      await apiClient.post('/orders', orderRequest);
      
      clearCart();
      toast.success('Order placed successfully! 🎉');
      navigate('/');
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to place order';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!user || user.type !== 'customer') {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800 mb-4">
            You must be logged in as a customer to access the cart
          </p>
          <Link to="/auth/login" className="btn-primary">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">Shopping Cart</h1>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🛒</div>
          <p className="text-gray-600 text-xl mb-6">Your cart is empty</p>
          <Link to="/dishes" className="btn-primary">
            Browse Menu
          </Link>
        </div>
      </div>
    );
  }

  const deliveryFee = 500; // $5 in cents
  const total = totalCost + deliveryFee;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">Shopping Cart</h1>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            {items.map((item) => (
              <div
                key={item.dish.id}
                className="bg-white rounded-lg shadow-md p-6 flex gap-4"
              >
                {/* Image */}
                <div className="w-24 h-24 flex-shrink-0">
                  {item.dish.picture ? (
                    <img
                      src={item.dish.picture}
                      alt={item.dish.name}
                      className="w-full h-full object-cover rounded-lg"
                    />
                  ) : (
                    <div className="w-full h-full bg-gray-200 rounded-lg flex items-center justify-center text-3xl">
                      🍽️
                    </div>
                  )}
                </div>

                {/* Details */}
                <div className="flex-1">
                  <Link
                    to={`/dishes/${item.dish.id}`}
                    className="text-lg font-semibold text-gray-900 hover:text-primary-600"
                  >
                    {item.dish.name}
                  </Link>
                  <p className="text-gray-600 mt-1">{item.dish.cost_formatted} each</p>

                  {/* Quantity Controls */}
                  <div className="flex items-center gap-4 mt-3">
                    <div className="flex items-center border border-gray-300 rounded-lg">
                      <button
                        onClick={() => updateQuantity(item.dish.id, item.quantity - 1)}
                        className="px-3 py-1 text-gray-600 hover:bg-gray-100 rounded-l-lg"
                      >
                        −
                      </button>
                      <span className="px-4 py-1 border-x border-gray-300">{item.quantity}</span>
                      <button
                        onClick={() => updateQuantity(item.dish.id, item.quantity + 1)}
                        className="px-3 py-1 text-gray-600 hover:bg-gray-100 rounded-r-lg"
                      >
                        +
                      </button>
                    </div>

                    <button
                      onClick={() => removeFromCart(item.dish.id)}
                      className="text-red-600 hover:text-red-700 text-sm font-medium"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {/* Subtotal */}
                <div className="text-right">
                  <p className="text-xl font-bold text-primary-600">
                    ${((item.dish.cost * item.quantity) / 100).toFixed(2)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-md p-6 sticky top-4">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Order Summary</h2>

            <form onSubmit={handleSubmitOrder}>
              {/* Delivery Address */}
              <div className="mb-6">
                <label
                  htmlFor="deliveryAddress"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Delivery Address *
                </label>
                <textarea
                  id="deliveryAddress"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  className="input-field resize-none"
                  rows={3}
                  placeholder="Enter your delivery address..."
                  required
                />
              </div>

              {/* Cost Breakdown */}
              <div className="space-y-3 mb-6 pb-6 border-b border-gray-200">
                <div className="flex justify-between text-gray-700">
                  <span>Subtotal</span>
                  <span>${(totalCost / 100).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-700">
                  <span>Delivery Fee</span>
                  <span>${(deliveryFee / 100).toFixed(2)}</span>
                </div>
              </div>

              <div className="flex justify-between text-xl font-bold text-gray-900 mb-6">
                <span>Total</span>
                <span>${(total / 100).toFixed(2)}</span>
              </div>

              {error && (
                <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full text-lg py-3"
              >
                {loading ? 'Placing Order...' : 'Place Order'}
              </button>
            </form>

            <button
              onClick={clearCart}
              className="w-full mt-3 text-center text-red-600 hover:text-red-700 text-sm font-medium py-2"
            >
              Clear Cart
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
