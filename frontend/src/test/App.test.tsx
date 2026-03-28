import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

// Mock the ApiStatus component to avoid API calls in tests
vi.mock('@/components/ApiStatus', () => ({
  ApiStatus: () => <div data-testid="api-status">API Status Mock</div>,
}))

describe('App', () => {
  it('renders the project name', () => {
    render(<App />)
    expect(screen.getByText('Exercise Competition')).toBeInTheDocument()
  })

  it('renders the project description', () => {
    render(<App />)
    expect(screen.getByText('Weekly exercise competition tracker for the Williams brothers')).toBeInTheDocument()
  })

  it('renders the counter button', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: /count is/i })).toBeInTheDocument()
  })

  it('renders the API status component', () => {
    render(<App />)
    expect(screen.getByTestId('api-status')).toBeInTheDocument()
  })
})
