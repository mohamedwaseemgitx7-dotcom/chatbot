import { useState } from 'react';

/**
 * useChat Hook Skeleton
 * Manages message history, loading states, and sending text queries.
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (text) => {
    // SKELETON: To be implemented in execution phase
  };

  return { messages, loading, sendMessage };
}
