/**
 * Mock data for dashboard development and testing
 * Matches DashboardData interface for type safety
 */

import type { DashboardData } from '@/types/dashboard';

export const mockDashboardData: DashboardData = {
  metrics: [
    {
      id: '1',
      title: 'Total Users',
      value: 12543,
      change: 12.5,
      trend: 'up'
    },
    {
      id: '2',
      title: 'Revenue',
      value: '$45,231',
      change: -2.3,
      trend: 'down'
    },
    {
      id: '3',
      title: 'Active Sessions',
      value: 892,
      change: 5.2,
      trend: 'up'
    },
    {
      id: '4',
      title: 'Conversion Rate',
      value: '3.2%',
      trend: 'neutral'
    },
    // Feature 2: Customer Metrics
    {
      id: '5',
      title: 'Total Customers',
      value: 8420,
      change: 8.3,
      trend: 'up'
    },
    {
      id: '6',
      title: 'New Customers (This Week)',
      value: 234,
      change: 15.7,
      trend: 'up'
    },
    {
      id: '7',
      title: 'Active Customers (Last 7 Days)',
      value: 3421,
      change: 4.2,
      trend: 'up'
    }
  ],
  charts: [
    {
      id: '1',
      type: 'line',
      title: 'User Growth',
      color: '#3b82f6',
      data: [
        { date: '2024-01', value: 1000 },
        { date: '2024-02', value: 1200 },
        { date: '2024-03', value: 1500 },
        { date: '2024-04', value: 1800 },
        { date: '2024-05', value: 2100 },
        { date: '2024-06', value: 2400 }
      ]
    },
    {
      id: '2',
      type: 'bar',
      title: 'Revenue by Category',
      color: '#4f46e5',
      data: [
        { category: 'Product A', value: 12000 },
        { category: 'Product B', value: 19000 },
        { category: 'Product C', value: 8000 },
        { category: 'Product D', value: 15000 }
      ]
    },
    {
      id: '3',
      type: 'pie',
      title: 'User Distribution',
      data: [
        { name: 'Desktop', value: 45 },
        { name: 'Mobile', value: 35 },
        { name: 'Tablet', value: 20 }
      ]
    },
    // Feature 1: API Calls Chart (Last 7 Days)
    {
      id: '4',
      type: 'line',
      title: 'API Calls (Last 7 Days)',
      color: '#8b5cf6',
      data: [
        { date: '2024-01-22', value: 1250 },
        { date: '2024-01-23', value: 1380 },
        { date: '2024-01-24', value: 1520 },
        { date: '2024-01-25', value: 1420 },
        { date: '2024-01-26', value: 1680 },
        { date: '2024-01-27', value: 1750 },
        { date: '2024-01-28', value: 1890 }
      ]
    },
    // Feature 3: Session Replay - Top Clicked Elements
    {
      id: '5',
      type: 'bar',
      title: 'Top Clicked Elements',
      color: '#7c3aed',
      data: [
        { category: 'Login Button', value: 1250 },
        { category: 'Search Bar', value: 980 },
        { category: 'Product Card', value: 750 },
        { category: 'Add to Cart', value: 520 },
        { category: 'Checkout Button', value: 480 },
        { category: 'Profile Icon', value: 420 },
        { category: 'Settings Menu', value: 380 },
        { category: 'Notifications', value: 320 },
        { category: 'Help Button', value: 280 },
        { category: 'Logout Button', value: 150 }
      ]
    }
  ]
};
