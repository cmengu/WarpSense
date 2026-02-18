// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// JSDOM does not provide IntersectionObserver; landing page uses useInView which depends on it.
class MockIntersectionObserver {
  observe = jest.fn()
  disconnect = jest.fn()
  unobserve = jest.fn()
}
global.IntersectionObserver = MockIntersectionObserver
