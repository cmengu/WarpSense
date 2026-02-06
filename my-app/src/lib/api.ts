/**
 * API client utility for fetching dashboard data from FastAPI backend
 * This replaces local mock data - backend is now the single source of truth
 */

import type { DashboardData } from '@/types/dashboard';

// API URL from environment variable, fallback to localhost:8000 for development
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Fetches dashboard data from the FastAPI backend
 * @returns Promise resolving to DashboardData
 * @throws Error if the request fails
 */
export async function fetchDashboardData(): Promise<DashboardData> {
  const response = await fetch(`${API_URL}/api/dashboard`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard data: ${response.statusText}`);
  }
  
  return response.json();
}
