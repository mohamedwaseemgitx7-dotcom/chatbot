/**
 * Session + error handling shared by the Supabase data services.
 * Raw Supabase/PostgREST errors are logged for developers and turned into plain messages for farmers.
 */
import { getSupabase } from "../lib/supabase";

/** kind: "network" | "auth" | "permission" | "not-found" | "too-large" | "file-type" | "unavailable" | "unknown" */
export class CloudError extends Error {
  constructor(kind, message, cause) {
    super(message);
    this.name = "CloudError";
    this.kind = kind;
    this.cause = cause;
  }
}

const MESSAGES = {
  network: "Unable to connect to the server. Please check your internet connection and try again.",
  auth: "Your session has expired. Please refresh the page and try again.",
  permission: "You don't have permission to do that.",
  "not-found": "This conversation couldn't be found. It may have been deleted.",
  "too-large": "This file is too large. Please choose a photo under 5 MB.",
  "file-type": "This file type isn't supported. Please use a JPG, PNG or WEBP photo.",
  unavailable: "Saving to the server isn't available right now.",
  unknown: "Something went wrong while saving. Please try again.",
};

function classify(error) {
  if (!error) return "unknown";
  if (error instanceof CloudError) return error.kind;
  const status = Number(error.status ?? error.statusCode ?? 0);
  const code = String(error.code ?? "");
  const text = `${error.name ?? ""} ${error.message ?? ""}`.toLowerCase();

  if (typeof navigator !== "undefined" && navigator.onLine === false) return "network";
  if (text.includes("failed to fetch") || text.includes("network") || text.includes("fetch failed") || error.name === "AuthRetryableFetchError") {
    return "network";
  }
  if (status === 401 || code === "PGRST301" || text.includes("jwt") || error.name?.startsWith("Auth")) return "auth";
  if (status === 403 || code === "42501" || text.includes("row-level security") || text.includes("permission")) return "permission";
  if (status === 404 || code === "PGRST116") return "not-found";
  if (status === 413 || text.includes("too large") || text.includes("exceeded the maximum")) return "too-large";
  if (status === 415 || text.includes("mime type") || text.includes("invalid_mime")) return "file-type";
  if (status >= 500) return "unavailable";
  return "unknown";
}

/** Wraps any Supabase failure in a CloudError with a farmer-friendly message. */
export function toCloudError(error, context = "") {
  if (error instanceof CloudError) return error;
  const kind = classify(error);
  if (import.meta.env.DEV) console.warn(`[FarmerAssist] Supabase ${context || "request"} failed:`, error);
  return new CloudError(kind, MESSAGES[kind], error);
}

/** Throws a CloudError when a supabase-js result carries an error; returns data otherwise. */
export function unwrap({ data, error }, context) {
  if (error) throw toCloudError(error, context);
  return data;
}

async function establishSession() {
  const supabase = await getSupabase();
  if (!supabase) throw new CloudError("unavailable", MESSAGES.unavailable);

  try {
    const { data } = await supabase.auth.getSession();
    if (data?.session?.user) return { supabase, userId: data.session.user.id };

    const { data: signIn, error } = await supabase.auth.signInAnonymously();
    if (error) {
      if (/anonymous sign-ins are disabled/i.test(error.message || "")) {
        console.warn("[FarmerAssist] Enable anonymous sign-ins in Supabase (Authentication → Sign In / Providers) to save chats to the server.");
      }
      throw error;
    }
    return { supabase, userId: signIn.user.id };
  } catch (error) {
    throw toCloudError(error, "sign-in");
  }
}

let sessionPromise = null;

/**
 * A client plus a signed-in user. Farmers don't log in yet, so each browser gets an anonymous account.
 * Concurrent callers share one sign-in, so a browser never creates two accounts at once.
 */
export function getSession() {
  sessionPromise ??= establishSession().catch((error) => {
    sessionPromise = null; // allow a retry later (e.g. when the network returns)
    throw error;
  });
  return sessionPromise;
}
