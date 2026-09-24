/**
 * Maps any thrown error to a farmer-friendly message. Raw error text, status codes and
 * stack traces are never shown to the user.
 */
import { ApiError } from "./http";

const ACTION = {
  chat: "processing your question",
  image: "analysing your photo",
  voice: "processing your voice message",
};

/**
 * @param {unknown} error
 * @param {"chat" | "image" | "voice"} context
 * @returns {{ message: string, retryable: boolean }}
 */
export function toFriendlyError(error, context = "chat") {
  const kind = error instanceof ApiError ? error.kind : "unknown";
  const status = error instanceof ApiError ? error.status : 0;
  const action = ACTION[context] || ACTION.chat;

  if (kind === "offline") {
    return { message: "You're offline. Check your internet connection and try again.", retryable: true };
  }
  if (kind === "network") {
    return { message: "Can't reach FarmerAssist right now. Please check your connection and try again.", retryable: true };
  }
  if (kind === "timeout" || status === 408) {
    return { message: "This is taking longer than expected. Please try again.", retryable: true };
  }
  if (kind === "unavailable") {
    return { message: "This feature isn't available yet.", retryable: false };
  }

  switch (status) {
    case 400:
    case 422:
      if (context === "image") {
        return { message: "This photo couldn't be read. Please use a clear JPG, PNG or WEBP photo of the crop.", retryable: false };
      }
      if (context === "voice") {
        return { message: "This recording couldn't be read. Please record again.", retryable: false };
      }
      return { message: "We couldn't understand that message. Please rephrase it and try again.", retryable: false };
    case 401:
    case 403:
      return { message: "You don't have access to this right now. Please refresh the page and try again.", retryable: false };
    case 404:
      return { message: "This service isn't available right now. Please try again later.", retryable: true };
    case 413:
      return { message: "This file is too large. Please choose a photo under 5 MB.", retryable: false };
    case 429: {
      const wait = error instanceof ApiError && error.retryAfter ? ` Try again in ${error.retryAfter} seconds.` : " Please wait a moment and try again.";
      return { message: `You've reached the request limit.${wait}`, retryable: true };
    }
    case 503:
      if (context === "voice") {
        return { message: "Voice input isn't available on this server yet. Please type your question instead.", retryable: false };
      }
      return { message: "FarmerAssist is temporarily unavailable. Please try again in a moment.", retryable: true };
    case 502:
    case 504:
      return { message: "FarmerAssist is temporarily unavailable. Please try again in a moment.", retryable: true };
    default:
      return { message: `Something went wrong while ${action}. Please try again.`, retryable: true };
  }
}
