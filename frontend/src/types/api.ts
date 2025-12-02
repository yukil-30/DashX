// API Types based on backend schemas
export interface Dish {
  id: number;
  name: string;
  description: string | null;
  cost: number;
  cost_formatted: string;
  picture: string | null;
  average_rating: number;
  reviews: number;
  chefID: number | null;
  restaurantID: number;
}

export interface DishListResponse {
  dishes: Dish[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface HomeResponse {
  most_ordered: Dish[];
  top_rated: Dish[];
  is_personalized: boolean;
}

export interface User {
  ID: number;
  email: string;
  type: 'customer' | 'visitor' | 'chef' | 'delivery' | 'manager';
  balance: number;
  warnings: number;
  wage: number | null;
  restaurantID: number | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  type: 'customer' | 'visitor';
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  warning_info?: {
    warnings_count: number;
    warning_message: string | null;
    is_near_threshold: boolean;
  };
}

export interface ProfileResponse {
  user: User;
}

export interface OrderedDish {
  dishID: number;
  name: string;
  quantity: number;
  price_at_order: number;
}

export interface Order {
  id: number;
  accountID: number;
  status: string;
  total_cost: number;
  total_cost_formatted: string;
  delivery_cost: number;
  delivery_cost_formatted: string;
  discount_applied: number;
  discount_applied_formatted: string;
  delivery_address: string;
  created_at: string;
  ordered_dishes: OrderedDish[];
  assigned_delivery_person_id: number | null;
}

export interface CreateOrderItem {
  dish_id: number;
  quantity: number;
}

export interface CreateOrderRequest {
  items: CreateOrderItem[];
  delivery_address: string;
}

export interface Bid {
  id: number;
  orderID: number;
  deliveryPersonID: number;
  bid_amount: number;
  bid_amount_formatted: string;
  status: string;
  created_at: string;
  delivery_person_email?: string;
}

export interface DeliveryPersonStats {
  delivery_person_id: number;
  email: string;
  total_deliveries: number;
  average_rating: number;
  on_time_percentage: number;
  warnings_count: number;
}

export interface BidWithStats extends Bid {
  stats: DeliveryPersonStats;
  is_lowest_bid: boolean;
}

export interface ChatMessage {
  id: number;
  question: string;
  answer: string;
  source: 'kb' | 'llm';
  rating: number | null;
  created_at: string;
}

export interface ChatQueryRequest {
  question: string;
}

export interface ChatQueryResponse {
  chat_id: number;
  question: string;
  answer: string;
  source: 'kb' | 'llm';
  confidence: number | null;
}

export interface ChatRateRequest {
  rating: number;
}

export interface Complaint {
  id: number;
  order_id: number;
  complaint_text: string;
  created_at: string;
  resolved_at: string | null;
  resolution_notes: string | null;
}
