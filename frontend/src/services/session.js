/**
 * Login session (token issued by the backend's /api/auth/login). Kept in localStorage until it expires.
 * The browser never checks passwords — it only stores the signed token the server returns.
 */
const KEY = "farmerassist.session.v1";
export const UNAUTHORIZED_EVENT = "farmerassist:unauthorized";

// Safari with "Block All Cookies" (and some in-app browsers) throws on localStorage. The session is then
// kept in memory, so it lasts until the tab is closed instead of being lost right after login.
let memorySession = null;

const isValid = (session) => Boolean(session?.token && session.expiresAt * 1000 > Date.now());

export function getSession() {
  try {
    const session = JSON.parse(localStorage.getItem(KEY) || "null");
    if (isValid(session)) return session;
  } catch {
    // storage blocked or unreadable → fall back to the in-memory copy
  }
  return isValid(memorySession) ? memorySession : null;
}

export function saveSession(session) {
  memorySession = session;
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // storage blocked: the in-memory copy keeps the session for this tab
  }
}

export function clearSession() {
  memorySession = null;
  try {
    localStorage.removeItem(KEY);
  } catch {
    // nothing to clear
  }
}

/** Called by the HTTP layer when the server rejects the token (expired, revoked, secret rotated). */
export function reportUnauthorized() {
  clearSession();
  window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
}
