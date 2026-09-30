/**
 * Low-level HTTP helpers. Every failure becomes an ApiError with a `kind`,
 * so the UI never has to look at raw fetch/XHR errors.
 * Requests carry the login token; a 401 logs the user out (session expired or revoked).
 */
import { getSession, reportUnauthorized } from "./session";

// Empty in dev: Vite proxies /api to the backend (see vite.config.js).
// Production: VITE_API_BASE_URL=https://<render-service>.onrender.com (VITE_API_URL is accepted too).
const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

/** kind: "offline" | "network" | "timeout" | "http" | "bad-response" | "unavailable" | "aborted" */
export class ApiError extends Error {
  constructor(kind, status = 0, retryAfter = null) {
    super(status ? `${kind} ${status}` : kind);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.retryAfter = retryAfter; // seconds, from the Retry-After header of a 429
  }
}

const isOffline = () => typeof navigator !== "undefined" && navigator.onLine === false;

function parseRetryAfter(value) {
  const seconds = Number.parseInt(value || "", 10);
  return Number.isFinite(seconds) && seconds > 0 ? Math.min(seconds, 3600) : null;
}

function authHeaders(useAuth) {
  const token = useAuth ? getSession()?.token : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function httpError(status, retryAfterHeader, needsAuth) {
  // A 401 on a request that needs login means the session is gone (expired, revoked, or never stored) → log in again.
  if (status === 401 && needsAuth) reportUnauthorized();
  return new ApiError("http", status, status === 429 ? parseRetryAfter(retryAfterHeader) : null);
}

/** Links an optional caller signal (e.g. a Cancel button) to our timeout controller. */
function linkSignal(controller, signal) {
  if (!signal) return;
  if (signal.aborted) controller.abort();
  else signal.addEventListener("abort", () => controller.abort(), { once: true });
}

/** POST/GET JSON (or FormData) with a timeout. Resolves to parsed JSON. `auth: false` for the login call. */
export async function requestJson(path, { method = "POST", json, form, timeoutMs = 30000, signal, auth = true } = {}) {
  if (isOffline()) throw new ApiError("offline");

  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  linkSignal(controller, signal);
  const headers = { ...authHeaders(auth), ...(json ? { "Content-Type": "application/json" } : {}) };

  let response;
  try {
    response = await fetch(`${API_BASE}/api${path}`, {
      method,
      headers,
      body: json ? JSON.stringify(json) : form,
      signal: controller.signal,
    });
  } catch {
    if (timedOut) throw new ApiError("timeout");
    if (signal?.aborted) throw new ApiError("aborted");
    throw new ApiError(isOffline() ? "offline" : "network");
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) throw httpError(response.status, response.headers.get("Retry-After"), auth);
  try {
    return await response.json();
  } catch {
    throw new ApiError("bad-response");
  }
}

/**
 * Multipart upload via XHR, because fetch cannot report when the upload itself has finished.
 * `onUploaded` fires once the file is on the server and it starts processing.
 */
export function uploadForm(path, form, { timeoutMs = 60000, onUploaded, signal } = {}) {
  if (isOffline()) return Promise.reject(new ApiError("offline"));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api${path}`);
    const headers = authHeaders(true);
    Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.timeout = timeoutMs;
    xhr.responseType = "text";

    xhr.upload.onload = () => onUploaded?.();
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        return reject(httpError(xhr.status, xhr.getResponseHeader("Retry-After"), true));
      }
      try {
        resolve(JSON.parse(xhr.responseText));
      } catch {
        reject(new ApiError("bad-response"));
      }
    };
    xhr.onerror = () => reject(new ApiError(isOffline() ? "offline" : "network"));
    xhr.ontimeout = () => reject(new ApiError("timeout"));
    xhr.onabort = () => reject(new ApiError("aborted"));

    if (signal) {
      if (signal.aborted) return xhr.abort();
      signal.addEventListener("abort", () => xhr.abort(), { once: true });
    }
    xhr.send(form);
  });
}
