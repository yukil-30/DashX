import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import toast from 'react-hot-toast';
import { Dish } from '../types/api';

interface CartItem {
  dish: Dish;
  quantity: number;
}

interface CartContextType {
  items: CartItem[];
  addToCart: (dish: Dish, quantity?: number) => void;
  removeFromCart: (dishId: number) => void;
  updateQuantity: (dishId: number, quantity: number) => void;
  clearCart: () => void;
  totalItems: number;
  totalCost: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);

  // Load cart from localStorage on mount
  useEffect(() => {
    const savedCart = localStorage.getItem('cart');
    if (savedCart) {
      try {
        setItems(JSON.parse(savedCart));
      } catch (e) {
        console.error('Failed to load cart:', e);
      }
    }
  }, []);

  // Save cart to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('cart', JSON.stringify(items));
  }, [items]);

  const addToCart = (dish: Dish, quantity = 1) => {
    setItems((prevItems) => {
      const existingItem = prevItems.find((item) => item.dish.id === dish.id);
      if (existingItem) {
        //toast.success(`Added ${quantity} more ${dish.name} to cart`);
        return prevItems.map((item) =>
          item.dish.id === dish.id
            ? { ...item, quantity: item.quantity + quantity }
            : item
        );
      } else {
        //toast.success(`${dish.name} added to cart`);
        return [...prevItems, { dish, quantity }];
      }
    });
  };

  const removeFromCart = (dishId: number) => {
    setItems((prevItems) => {
      const item = prevItems.find((item) => item.dish.id === dishId);
      if (item) {
        toast.success(`${item.dish.name} removed from cart`);
      }
      return prevItems.filter((item) => item.dish.id !== dishId);
    });
  };

  const updateQuantity = (dishId: number, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(dishId);
    } else {
      setItems((prevItems) =>
        prevItems.map((item) =>
          item.dish.id === dishId ? { ...item, quantity } : item
        )
      );
    }
  };

  const clearCart = () => {
    if (items.length > 0) {
      toast.success('Cart cleared');
    }
    setItems([]);
  };

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalCost = items.reduce((sum, item) => sum + item.dish.cost * item.quantity, 0);

  return (
    <CartContext.Provider
      value={{
        items,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        totalItems,
        totalCost,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}
