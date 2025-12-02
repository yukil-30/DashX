import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import DishCard from '../DishCard';
import { BrowserRouter } from 'react-router-dom';
import { Dish } from '../../types/api';

// Mock dish data
const mockDish: Dish = {
  id: 1,
  name: 'Test Dish',
  description: 'A delicious test dish',
  cost: 1299,
  cost_formatted: '$12.99',
  picture: null,
  average_rating: 4.5,
  reviews: 10,
  chefID: 1,
  restaurantID: 1,
};

describe('DishCard', () => {
  it('renders dish name', () => {
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    expect(screen.getByText('Test Dish')).toBeDefined();
  });

  it('renders dish price', () => {
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    expect(screen.getByText('$12.99')).toBeDefined();
  });

  it('renders dish rating', () => {
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    // Check for review count
    expect(screen.getByText(/10 reviews/)).toBeDefined();
  });

  it('renders dish image placeholder when no picture', () => {
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    // Check for emoji placeholder
    expect(screen.getByText('🍽️')).toBeDefined();
  });

  it('renders add to cart button when callback provided', () => {
    const mockAddToCart = vi.fn();
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} onAddToCart={mockAddToCart} />
      </BrowserRouter>
    );
    expect(screen.getByText('Add to Cart')).toBeDefined();
  });

  it('does not render add to cart button when no callback', () => {
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    expect(screen.queryByText('Add to Cart')).toBeNull();
  });

  it('renders dish description', () => {
    render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    expect(screen.getByText('A delicious test dish')).toBeDefined();
  });

  it('has correct test id', () => {
    const { container } = render(
      <BrowserRouter>
        <DishCard dish={mockDish} />
      </BrowserRouter>
    );
    expect(container.querySelector('[data-testid="dish-card"]')).toBeDefined();
  });
});
