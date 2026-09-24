import React, { createContext, useContext } from 'react';

/**
 * ChatContext Skeleton
 * Global state provider for conversation threads, active chat, and settings.
 */
const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  // SKELETON: Global state to be wired up in feature phase
  const value = {};
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChatContext() {
  return useContext(ChatContext);
}
