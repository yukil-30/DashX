import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders the app logo emoji', () => {
    render(<App />)
    expect(screen.getByText(/🍽️/)).toBeInTheDocument()
  })

  it('renders navigation menu link', () => {
    render(<App />)
    expect(screen.getByText(/Menu/i)).toBeInTheDocument()
  })

  it('renders support link', () => {
    render(<App />)
    expect(screen.getByText(/Support/i)).toBeInTheDocument()
  })

  it('renders login button when not authenticated', () => {
    render(<App />)
    expect(screen.getByText(/Login/i)).toBeInTheDocument()
  })

  it('renders sign up button when not authenticated', () => {
    render(<App />)
    expect(screen.getByText(/Sign Up/i)).toBeInTheDocument()
  })

  it('renders footer with copyright', () => {
    render(<App />)
    expect(screen.getByText(/2025/i)).toBeInTheDocument()
  })
})
