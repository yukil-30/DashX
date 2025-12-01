/**
 * Order and Bid type definitions
 */

export interface OrderedDish {
  DishID: number;
  quantity: number;
  dish_name: string | null;
  dish_cost: number | null;
}

export interface Order {
  id: number;
  accountID: number;
  dateTime: string | null;
  finalCost: number;
  status: string;
  bidID: number | null;
  note: string | null;
  delivery_address: string | null;
  delivery_fee: number;
  subtotal_cents: number;
  discount_cents: number;
  free_delivery_used: number;
  ordered_dishes: OrderedDish[];
}

export interface DeliveryPersonStats {
  account_id: number;
  email: string;
  average_rating: number;
  reviews: number;
  total_deliveries: number;
  on_time_deliveries: number;
  on_time_percentage: number;
  avg_delivery_minutes: number;
  warnings: number;
}

export interface BidWithStats {
  id: number;
  deliveryPersonID: number;
  orderID: number;
  bidAmount: number;
  estimated_minutes: number;
  is_lowest: boolean;
  delivery_person: DeliveryPersonStats;
}

export interface BidListResponse {
  order_id: number;
  bids: BidWithStats[];
  lowest_bid_id: number | null;
}

export interface AssignDeliveryRequest {
  delivery_id: number;
  memo?: string;
}

export interface AssignDeliveryResponse {
  message: string;
  order_id: number;
  assigned_delivery_id: number;
  bid_id: number;
  delivery_fee: number;
  order_status: string;
  is_lowest_bid: boolean;
  memo_saved: boolean;
}

// Helper to format cents to dollars
export const formatCents = (cents: number): string => {
  return `$${(cents / 100).toFixed(2)}`;
};
