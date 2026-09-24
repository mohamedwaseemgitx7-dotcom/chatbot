/**
 * The one Supabase client for the browser.
 *
 * Only the project URL and the publishable (anon) key belong here. Row Level Security decides what
 * each user may read or write. The secret / service-role key must never reach the frontend.
 * supabase-js is loaded on demand so it doesn't delay the first render.
 */
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || "").trim().replace(/\/(rest\/v1)?\/?$/, "");
const SUPABASE_KEY = (import.meta.env.VITE_SUPABASE_ANON_KEY || "").trim();

function looksLikeSecretKey(key) {
  if (key.startsWith("sb_secret_")) return true;
  try {
    const payload = JSON.parse(atob(key.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload?.role === "service_role";
  } catch {
    return false;
  }
}

function configProblem() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return "VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set in frontend/.env — conversations are saved in this browser only.";
  }
  if (looksLikeSecretKey(SUPABASE_KEY)) {
    return "VITE_SUPABASE_ANON_KEY is a secret/service-role key. Never put it in the frontend — use the publishable (anon) key. Cloud sync is disabled.";
  }
  return null;
}

const problem = configProblem();
if (problem) console.warn(`[FarmerAssist] ${problem}`);

export const supabaseConfigured = problem === null;

let clientPromise = null;

/** @returns {Promise<import("@supabase/supabase-js").SupabaseClient | null>} */
export function getSupabase() {
  if (!supabaseConfigured) return Promise.resolve(null);
  clientPromise ??= import("@supabase/supabase-js").then(({ createClient }) =>
    createClient(SUPABASE_URL, SUPABASE_KEY, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    }),
  );
  return clientPromise;
}
