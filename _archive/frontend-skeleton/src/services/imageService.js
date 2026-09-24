import { API_BASE_URL } from './api';

/**
 * Image Service Skeleton
 * Interfaces with POST /api/image/analyze
 */
export async function analyzeCropImage(file, conversationId = null) {
  // SKELETON: Business logic to be implemented in feature phase
  const formData = new FormData();
  formData.append('file', file);
  if (conversationId) formData.append('conversation_id', conversationId);

  const response = await fetch(`${API_BASE_URL}/api/image/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Image analysis failed');
  }

  return response.json();
}
