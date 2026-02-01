/**
 * Backend API Client
 * REST calls to FastAPI backend
 * 
 * Placeholder functions - implementation will be added later
 */

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Send session data to backend
 * @param sessionData - Session JSON data
 */
export async function sendSession(sessionData: any): Promise<void> {
  // TODO: Implement session sending logic
  throw new Error('Not implemented yet');
}

/**
 * Fetch session data from backend
 * @param sessionId - Session ID
 */
export async function fetchSession(sessionId: string): Promise<any> {
  // TODO: Implement session fetching logic
  throw new Error('Not implemented yet');
}

/**
 * List all sessions
 */
export async function listSessions(): Promise<any[]> {
  // TODO: Implement session listing logic
  throw new Error('Not implemented yet');
}
