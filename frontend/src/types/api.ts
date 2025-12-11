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
  is_specialty: boolean;
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
  customer_tier?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
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

// KB Contribution Types
export interface KBContributionCreateRequest {
  question: string;
  answer: string;
  keywords?: string;
}

export interface KBContributionResponse {
  id: number;
  submitter_id: number;
  submitter_email: string | null;
  question: string;
  answer: string;
  keywords: string | null;
  status: 'pending' | 'approved' | 'rejected';
  rejection_reason: string | null;
  reviewed_by: number | null;
  reviewer_email: string | null;
  reviewed_at: string | null;
  created_kb_entry_id: number | null;
  created_at: string | null;
}

export interface KBContributionListResponse {
  contributions: KBContributionResponse[];
  total: number;
  pending_count: number;
}

export interface MyKBContributionsResponse {
  contributions: {
    id: number;
    question: string;
    answer: string;
    status: 'pending' | 'approved' | 'rejected';
    rejection_reason: string | null;
    created_at: string | null;
  }[];
  total: number;
}

// Complaints & Compliments
export interface Complaint {
  id: number;
  accountID: number | null;
  type: 'complaint' | 'compliment';
  description: string;
  filer: number;
  filer_email: string | null;
  about_email: string | null;
  order_id: number | null;
  status: 'pending' | 'resolved' | 'disputed';
  resolution: string | null;
  resolved_by: number | null;
  resolved_at: string | null;
  created_at: string;
  disputed: boolean;
  dispute_reason: string | null;
  disputed_at: string | null;
  target_type: 'chef' | 'delivery' | 'customer' | null;
}

export interface ComplaintCreateRequest {
  about_user_id: number | null;
  order_id: number | null;
  type: 'complaint' | 'compliment';
  text: string;
  target_type?: 'chef' | 'delivery' | 'customer';
}

export interface ComplaintListResponse {
  complaints: Complaint[];
  total: number;
  unresolved_count: number;
}

export interface DisputeRequest {
  reason: string;
}

export interface DisputeResponse {
  message: string;
  complaint_id: number;
  disputed: boolean;
  dispute_reason: string;
  status: string;
  disputed_at: string;
}

// VIP Status
export interface VIPStatus {
  is_vip: boolean;
  total_spent_cents: number;
  total_spent_formatted: string;
  completed_orders: number;
  has_unresolved_complaints: boolean;
  vip_eligible: boolean;
  vip_reason: string | null;
  free_delivery_credits: number;
  discount_percent: number;
  next_free_delivery_in: number;
}

// Customer Dashboard
export interface OrderSummary {
  id: number;
  status: string;
  total_cents: number;
  total_formatted: string;
  items_count: number;
  created_at: string;
  can_review: boolean;
}

export interface ChefProfileSummary {
  id: number;
  email: string;
  display_name: string | null;
  profile_picture: string | null;
  specialty: string | null;
  average_rating: number;
  total_dishes: number;
  total_reviews: number;
}

export interface CustomerDashboardResponse {
  user_id: number;
  email: string;
  account_type: string;
  balance_cents: number;
  balance_formatted: string;
  vip_status: VIPStatus;
  recent_orders: OrderSummary[];
  favorite_dishes: Dish[];
  most_popular_dish: Dish | null;
  highest_rated_dish: Dish | null;
  top_rated_chef: ChefProfileSummary | null;
}

// Profiles
export interface ProfileData {
  account_id: number;
  email: string;
  account_type: string;
  display_name: string | null;
  bio: string | null;
  profile_picture: string | null;
  phone: string | null;
  address: string | null;
  specialty: string | null;
  created_at: string | null;
  total_orders: number;
  total_reviews_given: number;
  average_rating_given: number;
  dishes_created: number;
  average_dish_rating: number;
  total_deliveries: number;
  average_delivery_rating: number;
  on_time_percentage: number;
}

export interface ChefProfile extends ProfileData {
  dishes: Dish[];
}

// Forum
export interface ForumPost {
  id: number;
  threadID: number;
  posterID: number;
  title: string | null;
  body: string;
  datetime: string | null;
}

export interface ForumThread {
  id: number;
  topic: string;
  restaurantID: number;
  created_by_id: number;
  created_by_email: string | null;
  category: string | null;
  posts_count: number;
  created_at: string | null;
  posts: ForumPost[];
}

export interface ThreadListResponse {
  threads: ForumThread[];
  total: number;
  page: number;
  per_page: number;
}

// Reviews
export interface DishReview {
  id: number;
  dish_id: number;
  dish_name: string;
  account_id: number;
  reviewer_email: string | null;
  order_id: number | null;
  rating: number;
  review_text: string | null;
  created_at: string;
}

export interface DeliveryReview {
  id: number;
  order_id: number;
  delivery_person_id: number;
  delivery_person_email: string | null;
  reviewer_id: number;
  rating: number;
  review_text: string | null;
  on_time: boolean | null;
  created_at: string;
}

// Order History
export interface OrderHistoryItem {
  dish_id: number;
  dish_name: string;
  dish_picture: string | null;
  quantity: number;
  unit_price_cents: number;
  can_review: boolean;
  has_reviewed: boolean;
}

export interface OrderHistory {
  id: number;
  status: string;
  created_at: string;
  delivered_at: string | null;
  subtotal_cents: number;
  delivery_fee_cents: number;
  discount_cents: number;
  total_cents: number;
  total_formatted: string;
  delivery_address: string;
  note: string | null;
  items: OrderHistoryItem[];
  delivery_person_id: number | null;
  delivery_person_email: string | null;
  can_review_delivery: boolean;
  has_reviewed_delivery: boolean;
  free_delivery_used: boolean;
  vip_discount_applied: boolean;
}

export interface OrderHistoryListResponse {
  orders: OrderHistory[];
  total: number;
  page: number;
  per_page: number;
}

// Balance/Deposit
export interface BalanceResponse {
  balance_cents: number;
  balance_formatted: string;
}

export interface DepositRequest {
  amount_cents: number;
}

export interface DepositResponse {
  message: string;
  new_balance_cents: number;
  new_balance_formatted: string;
}

export interface TransactionItem {
  id: number;
  accountID: number;
  amount_cents: number;
  balance_before: number;
  balance_after: number;
  transaction_type: string;
  reference_type: string | null;
  reference_id: number | null;
  description: string | null;
  created_at: string;
}

export interface TransactionListResponse {
  transactions: TransactionItem[];
  total: number;
}

// ============================================================
// Reputation System Types
// ============================================================

export interface EmployeeReputationSummary {
  employee_id: number;
  email: string;
  type: 'chef' | 'delivery';
  employment_status: 'active' | 'demoted' | 'fired';
  
  // Rating metrics
  rolling_avg_rating: number;
  total_rating_count: number;
  
  // Complaint/compliment tracking
  complaint_count: number;
  compliment_count: number;
  
  // Status tracking
  demotion_count: number;
  bonus_count: number;
  is_fired: boolean;
  wage_cents: number | null;
  
  // Risk assessment
  near_demotion: boolean;
  near_firing: boolean;
  bonus_eligible: boolean;
  
  // Warning message for UI
  status_warning: string | null;
}

export interface CustomerWarningSummary {
  customer_id: number;
  email: string;
  type: 'customer' | 'vip' | 'visitor' | 'deregistered';
  customer_tier: 'registered' | 'vip' | 'deregistered';
  
  // Warning tracking
  warning_count: number;
  threshold: number;
  is_blacklisted: boolean;
  
  // Status flags
  near_threshold: boolean;
  has_active_dispute: boolean;
  
  // Message for UI
  warning_message: string | null;
}

export interface ReputationDashboardStats {
  // Employee stats
  total_employees: number;
  active_employees: number;
  demoted_employees: number;
  fired_employees: number;
  employees_near_demotion: number;
  employees_near_firing: number;
  employees_bonus_eligible: number;
  
  // Customer stats
  total_customers: number;
  vip_customers: number;
  customers_with_warnings: number;
  customers_near_deregistration: number;
  deregistered_customers: number;
  
  // Recent activity
  recent_demotions: number;
  recent_firings: number;
  recent_bonuses: number;
  recent_warnings_issued: number;
  recent_deregistrations: number;
  
  // Pending items
  pending_complaints: number;
  pending_disputes: number;
  pending_compliments: number;
}

export interface EmployeeListWithReputationResponse {
  employees: EmployeeReputationSummary[];
  total: number;
  chefs_count: number;
  delivery_count: number;
  at_risk_count: number;
  bonus_eligible_count: number;
}

export interface CustomerListWithWarningsResponse {
  customers: CustomerWarningSummary[];
  total: number;
  vip_count: number;
  at_risk_count: number;
  deregistered_count: number;
}

export interface Complaint {
  id: number;
  accountID: number | null;
  type: 'complaint' | 'compliment';
  description: string;
  filer: number;
  filer_email: string | null;
  about_email: string | null;
  order_id: number | null;
  status: 'pending' | 'resolved' | 'disputed';
  resolution: 'dismissed' | 'warning_issued' | null;
  resolved_by: number | null;
  resolved_at: string | null;
  created_at: string | null;
  disputed: boolean;
  dispute_reason: string | null;
  disputed_at: string | null;
  target_type: 'chef' | 'delivery' | 'customer' | null;
}

export interface ComplaintListResponse {
  complaints: Complaint[];
  total: number;
  unresolved_count: number;
}

export interface DisputeDetailResponse {
  complaint_id: number;
  complaint_type: 'complaint' | 'compliment';
  description: string;
  
  // Filer info
  filer_id: number;
  filer_email: string;
  filer_type: string;
  filer_warnings: number;
  
  // Target info
  target_id: number | null;
  target_email: string | null;
  target_type: string | null;
  target_warnings: number;
  target_complaint_count: number;
  target_compliment_count: number;
  target_avg_rating: number | null;
  
  // Order context
  order_id: number | null;
  order_status: string | null;
  
  // Dispute details
  status: string;
  disputed: boolean;
  dispute_reason: string | null;
  disputed_at: string | null;
  created_at: string | null;
  
  // Resolution preview
  resolution_preview: Record<string, unknown>;
}

export interface DisputeResolveRequest {
  resolution: 'upheld' | 'dismissed';
  notes?: string;
}

export interface DisputeResolveResponse {
  message: string;
  complaint_id: number;
  resolution: string;
  warning_applied_to: number | null;
  new_warning_count: number | null;
  vip_downgraded: boolean;
  customer_deregistered: boolean;
  employee_demoted: boolean;
  employee_fired: boolean;
  bonus_awarded: boolean;
  audit_log_id: number;
  actions_taken: string[];
}

export interface ComplaintCreateRequest {
  about_user_id?: number;
  order_id?: number;
  type: 'complaint' | 'compliment';
  text: string;
  target_type?: 'chef' | 'delivery' | 'customer';
}

export interface DisputeRequest {
  reason: string;
}

// Reputation Dashboard Types
export interface ReputationDashboardStats {
  // Employee stats
  total_employees: number;
  active_employees: number;
  demoted_employees: number;
  fired_employees: number;
  employees_near_demotion: number;
  employees_near_firing: number;
  employees_bonus_eligible: number;
  recent_bonuses: number;
  recent_firings: number;
  
  // Customer stats
  total_customers: number;
  vip_customers: number;
  customers_with_warnings: number;
  customers_near_deregistration: number;
  deregistered_customers: number;
  recent_deregistrations: number;
  
  // Complaint stats
  pending_complaints: number;
  pending_disputes: number;
}

export interface EmployeeReputationSummary {
  employee_id: number;
  email: string;
  type: 'chef' | 'delivery';
  rolling_avg_rating: number;
  total_ratings: number;
  complaint_count: number;
  compliment_count: number;
  demotion_count: number;
  employment_status: 'active' | 'demoted' | 'fired';
  is_fired: boolean;
  near_demotion: boolean;
  near_firing: boolean;
  bonus_eligible: boolean;
}

export interface CustomerWarningSummary {
  customer_id: number;
  email: string;
  customer_tier: 'customer' | 'vip';
  warning_count: number;
  threshold: number;
  near_threshold: boolean;
  is_blacklisted: boolean;
  has_active_dispute: boolean;
}

export interface EmployeeListWithReputationResponse {
  employees: EmployeeReputationSummary[];
  total: number;
  page: number;
  per_page: number;
}

export interface CustomerListWithWarningsResponse {
  customers: CustomerWarningSummary[];
  total: number;
  page: number;
  per_page: number;
}
