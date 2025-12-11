import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../lib/api-client';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

export default function ChefOrders() {
  const { user } = useAuth();
  const [dishes, setDishes] = useState<number[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [marking, setMarking] = useState<number | null>(null);

  useEffect(() => {
    if (user) loadData();
  }, [user]);

  const loadData = async () => {
    setLoading(true);
    try {
      // 1) fetch chef dishes to know which dish IDs belong to this chef
      const dishesResp = await apiClient.get(`/dishes?per_page=50&chef_id=${user?.ID}`);
      const chefDishes = dishesResp.data.dishes || [];
      const chefDishIds = chefDishes.map((d: any) => d.id);
      setDishes(chefDishIds);

      // 2) fetch recent orders for this chef (server-side filter)
      const ordersResp = await apiClient.get('/orders/chef', { params: { limit: 50 } });
      // Normalize response shape: backend may return an array or { orders: [...] }
      let allOrders: any[] = [];
      if (Array.isArray(ordersResp.data)) {
        allOrders = ordersResp.data;
      } else if (Array.isArray(ordersResp.data?.orders)) {
        allOrders = ordersResp.data.orders;
      } else if (Array.isArray(ordersResp.data?.data)) {
        allOrders = ordersResp.data.data;
      } else if (ordersResp.data) {
        // If it's an object with numeric keys or single order, try to extract
        try {
          allOrders = Object.values(ordersResp.data).filter(v => Array.isArray(v)).flat()[0] || [];
        } catch (e) {
          allOrders = [];
        }
      }

      const chefOrders = allOrders.filter((o: any) => {
        if (!o.ordered_dishes) return false;
        return o.ordered_dishes.some((od: any) => {
          const id = od.dish_id ?? od.dishID ?? od.DishID ?? od.DishId ?? od.id;
          return chefDishIds.includes(id);
        });
      });

      setOrders(chefOrders);
    } catch (err: any) {
      console.error('Failed to load chef orders:', err);
      const detail = err?.response?.data?.detail || err?.message || 'Failed to load orders';
      toast.error(typeof detail === 'string' ? detail : 'Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const markPrepared = async (orderId: number) => {
    setMarking(orderId);
    try {
      // Server-side endpoint now implemented at POST /orders/{id}/chef-mark-prepared
      await apiClient.post(`/orders/${orderId}/chef-mark-prepared`);
      toast.success('Marked as prepared');
      setOrders(prev => prev.filter(o => o.id !== orderId));
    } catch (err: any) {
      console.error('Failed to mark prepared:', err);
      toast.error(err?.response?.data?.detail || 'Failed to mark prepared');
    } finally {
      setMarking(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Active Orders</h1>
          <p className="text-gray-600">Orders containing your dishes — mark when prepared</p>
        </div>
        <div className="flex gap-3">
          <Link to="/chef/dashboard" className="btn-secondary">My Dishes</Link>
          <button onClick={refresh} className="btn-primary">{refreshing ? 'Refreshing...' : 'Refresh'}</button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : orders.length === 0 ? (
        <div className="p-6 bg-white rounded-xl shadow-md text-gray-600">No active orders for your dishes.</div>
      ) : (
        <div className="grid gap-4">
          {orders.map((order: any) => {
            const ordered = order.ordered_dishes || [];
            const chefItems = ordered.filter((od: any) => {
              const id = od.dish_id ?? od.dishID ?? od.DishID ?? od.DishId ?? od.id;
              return dishes.includes(id);
            });

            return (
              <div key={order.id} className="p-4 bg-white rounded-lg shadow">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold">Order #{order.id}</span>
                      <span className="text-sm text-gray-500">{order.created_at || order.dateTime || ''}</span>
                      <span className="ml-4 text-sm text-gray-600">{chefItems.length} item(s) for you</span>
                    </div>
                    <div className="text-sm text-gray-600 mt-2">📍 {order.delivery_address || 'Pickup / No address'}</div>

                    <ul className="mt-3 space-y-1">
                      {chefItems.map((it: any, idx: number) => {
                        const name = it.name ?? it.dish_name ?? it.dishName ?? it.title ?? 'Dish';
                        const qty = it.quantity ?? it.qty ?? it.count ?? 1;
                        return (
                          <li key={idx} className="text-sm text-gray-700">
                            • {name} <span className="text-gray-500">x{qty}</span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => markPrepared(order.id)}
                      className="btn-primary"
                      disabled={marking === order.id}
                    >
                      {marking === order.id ? 'Marking...' : '✓ Mark Prepared'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
