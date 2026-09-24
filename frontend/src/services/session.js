/**
 * Login session (token issued by the backend's /api/auth/login). Kept in localStorage until it expires.
 * The browser never checks passwords — it only stores the signed token the server returns.
 */
const KEY = "farmerassist.session.v1";
export const UNAUTHORIZED_EVENT = "farmerassist:unauthorized";

export function getSession() {
  try {
    const session = JSON.parse(localStorage.getItem(KEY) || "null");
    if (session?.token && session.expiresAt * 1000 > Date.now()) return session;
  } catch {
    // unreadable storage → treated as logged out
  }
  return null;
}

export function saveSession(session) {
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // storage blocked: the session lasts for this page only
  }
}

export function clearSession() {
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
