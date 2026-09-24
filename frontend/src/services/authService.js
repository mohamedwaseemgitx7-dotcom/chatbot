/**
 * Login / logout against the backend (/api/auth/*). Credentials are checked by the server only.
 */
import { requestJson } from "./http";
import { clearSession, getSession, saveSession } from "./session";

/** @returns {Promise<{ token: string, expiresAt: number, username: string }>} */
export async function login(username, password) {
  const data = await requestJson("/auth/login", { json: { username, password }, auth: false, timeoutMs: 20000 });
  if (typeof data?.token !== "string" || typeof data?.expires_at !== "number") throw new Error("bad login response");
  const session = { token: data.token, expiresAt: data.expires_at, username: String(data.username || username) };
  saveSession(session);
  return session;
}

/** Revokes the token on the server (best effort) and forgets it locally. */
export async function logout() {
  if (getSession()) {
    try {
      await requestJson("/auth/logout", { timeoutMs: 8000 });
    } catch {
      // offline or already expired — the local session is cleared either way
    }
  }
  clearSession();
}

/** Confirms the stored token is still accepted (a 401 triggers the unauthorized event). */
export async function verifySession() {
  return requestJson("/auth/me", { method: "GET", timeoutMs: 10000 });
}
