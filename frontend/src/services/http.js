/**
 * Low-level HTTP helpers. Every failure becomes an ApiError with a `kind`,
 * so the UI never has to look at raw fetch/XHR errors.
 */

// Empty in dev: Vite proxies /api to the backend (see vite.config.js).
// Production: VITE_API_BASE_URL=https://<render-service>.onrender.com (VITE_API_URL is accepted too).
const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

/** kind: "offline" | "network" | "timeout" | "http" | "bad-response" | "unavailable" | "aborted" */
export class ApiError extends Error {
  constructor(kind, status = 0) {
    super(status ? `${kind} ${status}` : kind);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

const isOffline = () => typeof navigator !== "undefined" && navigator.onLine === false;

/** Links an optional caller signal (e.g. a Cancel button) to our timeout controller. */
function linkSignal(controller, signal) {
  if (!signal) return;
  if (signal.aborted) controller.abort();
  else signal.addEventListener("abort", () => controller.abort(), { once: true });
}

/** POST/GET JSON (or FormData) with a timeout. Resolves to parsed JSON. */
export async function requestJson(path, { method = "POST", json, form, timeoutMs = 30000, signal } = {}) {
  if (isOffline()) throw new ApiError("offline");

  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  linkSignal(controller, signal);

  let response;
  try {
    response = await fetch(`${API_BASE}/api${path}`, {
      method,
      headers: json ? { "Content-Type": "application/json" } : undefined,
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

  if (!response.ok) throw new ApiError("http", response.status);
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
    xhr.timeout = timeoutMs;
    xhr.responseType = "text";

    xhr.upload.onload = () => onUploaded?.();
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) return reject(new ApiError("http", xhr.status));
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
