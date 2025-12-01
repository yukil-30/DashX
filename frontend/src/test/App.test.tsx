import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders the app title', () => {
    render(<App />)
    expect(screen.getByText(/Local AI-enabled Restaurant/i)).toBeInTheDocument()
  })

  it('renders the subtitle', () => {
    render(<App />)
    expect(screen.getByText(/Your intelligent dining companion/i)).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    render(<App />)
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('renders features section', () => {
    render(<App />)
    expect(screen.getByText(/Features/i)).toBeInTheDocument()
  })

  it('lists AI-powered menu recommendations feature', () => {
    render(<App />)
    expect(screen.getByText(/AI-powered menu recommendations/i)).toBeInTheDocument()
  })

  it('renders footer with copyright', () => {
    render(<App />)
    expect(screen.getByText(/2025/i)).toBeInTheDocument()
  })
})
