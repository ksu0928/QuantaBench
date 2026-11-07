/**
 * Jest setup file
 * Runs before all tests
 */

// Set test environment variables
process.env.NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
process.env.NEXT_PUBLIC_DEBUG = 'false'

// Global test utilities
global.console = {
  ...console,
  // Suppress console.log in tests unless explicitly needed
  log: jest.fn(),
  error: console.error,
  warn: console.warn,
  info: console.info,
  debug: console.debug,
}
