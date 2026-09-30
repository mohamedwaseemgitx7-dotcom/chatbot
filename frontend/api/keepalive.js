/**
 * Daily keep-alive, run by Vercel Cron (see vercel.json → "crons").
 * Calls the API's readiness check, which wakes the Render free instance and runs one small Supabase query.
 * Free Supabase projects pause after about a week without activity; this keeps the database awake.
 * Vercel sends `Authorization: Bearer $CRON_SECRET` on cron calls; other callers are refused.
 */
export default async function handler(request, response) {
  const secret = process.env.CRON_SECRET;
  if (!secret || request.headers.authorization !== `Bearer ${secret}`) {
    return response.status(401).json({ error: "unauthorized" });
  }

  const api = (process.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
  if (!api) return response.status(500).json({ error: "VITE_API_BASE_URL is not set" });

  try {
    // A sleeping Render instance takes 30–60 s to start.
    const res = await fetch(`${api}/api/health/ready`, { signal: AbortSignal.timeout(55_000) });
    const body = await res.json().catch(() => ({}));
    const ok = res.ok && body.database === "connected";
    return response.status(ok ? 200 : 502).json({ ok, status: res.status, database: body.database ?? null });
  } catch (error) {
    return response.status(502).json({ ok: false, error: String(error?.name || error) });
  }
}
