/**
 * Dish type definitions
 */

export interface DishImage {
  id: number;
  image_url: string;
  display_order: number;
}

export interface Dish {
  id: number;
  name: string;
  description: string | null;
  price_cents: number;
  price_formatted: string;
  category: string | null;
  is_available: boolean;
  is_special: boolean;
  average_rating: number;
  review_count: number;
  order_count: number;
  chef_id: number | null;
  chef_name: string | null;
  images: DishImage[];
  picture: string | null;
  created_at: string;
  updated_at: string;
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

export interface DishRateRequest {
  rating: number;
  order_id: number;
  review_text?: string;
}

export interface DishRateResponse {
  message: string;
  new_average_rating: number;
  review_count: number;
}
