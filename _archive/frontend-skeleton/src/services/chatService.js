import { request } from './api';

/**
 * Chat Service Skeleton
 * Interfaces with POST /api/chat
 */
export async function sendChatMessage(message, conversationId = null) {
  // SKELETON: Business logic to be implemented in feature phase
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}
