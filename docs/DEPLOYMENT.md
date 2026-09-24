# Deploying FarmerAssist

Order matters: **Supabase → backend locally → Render → test Render → frontend locally against Render → Vercel → end-to-end test.**

## 0. Push the repository to GitHub

The repo is initialised locally with a first commit (secrets excluded — `git check-ignore backend/.env frontend/.env` must print both).

```bash
# create an EMPTY private repo on github.com first, then:
git remote add origin https://github.com/<you>/farmerassist.git
git push -u origin main
```

## 1. Supabase (once)

1. SQL Editor → run, in order:
   - `supabase/migrations/20260924000000_initial_schema.sql` (already applied)
   - `supabase/migrations/20260924010000_knowledge_sources.sql` (knowledge provenance columns)
   - `supabase/migrations/20260924020000_prediction_versioning.sql` (model_name / model_version / dataset_version on image_predictions)
2. Authentication → Sign In / Providers → **Allow anonymous sign-ins** (already on).
3. Import the verified knowledge: `backend/.venv/Scripts/python scripts/import_supabase.py`
4. Recommended before public launch: Authentication → Attack Protection → CAPTCHA for sign-ins.

## 2. Backend locally

```bash
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # + requirements-voice.txt for voice
.venv/Scripts/python run.py            # http://127.0.0.1:8000/api/health/ready
cd .. && backend/.venv/Scripts/python -m pytest
```

## 3. Render (backend)

New → **Blueprint** → select the GitHub repo (uses `render.yaml`). Fill the secret values it asks for:

| Variable | Value |
|---|---|
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://farmerassist.vercel.app` (no trailing slash) |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | publishable key `sb_publishable_…` |
| `SUPABASE_SERVICE_ROLE_KEY` | secret key `sb_secret_…` (Render only — never in the frontend) |
| `DEMO_USERNAME` | the login name |
| `DEMO_PASSWORD_HASH` | output of `backend/.venv/Scripts/python scripts/hash_password.py` (the hash, never the password) |
| `SESSION_SECRET` | the random value printed by the same script (use a different one than local) |

Already set by the Blueprint: `ENVIRONMENT=production`, `TRUST_PROXY_HEADERS=true`, `VOICE_ENABLED=false`, `PYTHON_VERSION=3.13.1`.

Free-plan facts: 512 MB RAM, sleeps after 15 min idle (first request then takes ~30–60 s).
Voice stays off on the free plan (Whisper needs ~1 GB); the API answers `/api/voice/transcribe` with 503 and the app shows
"Voice input isn't available on this server yet". Upgrade to a 2 GB instance and set `VOICE_ENABLED=true` (and add
`faster-whisper` to requirements.txt) to enable it.

## 3b. Railway (alternative to Render)

New Project → Deploy from GitHub repo → select this repo, then in the service **Settings**:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Config file (Config-as-code) | `/backend/railway.json` (build: `pip install -r requirements.txt`, start: `python run.py`, health check `/api/health`) |
| Networking | Generate Domain (Railway sets `PORT`; `run.py` binds `0.0.0.0:$PORT`) |

Variables: the same as the Render table above, plus `ENVIRONMENT=production`, `TRUST_PROXY_HEADERS=true`,
`VOICE_ENABLED=false`. Python 3.13 comes from `backend/.python-version`. Use the Railway domain wherever this guide
says `<service>.onrender.com`.

## 4. Test the Render API

```bash
curl https://<service>.onrender.com/api/health
curl https://<service>.onrender.com/api/health/ready
# log in (prints a token), then call chat with it
curl -X POST https://<service>.onrender.com/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"<user>\",\"password\":\"<password>\"}"
curl -X POST https://<service>.onrender.com/api/chat -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"message\":\"How can I control stem borer in paddy?\"}"
```

## 5. Frontend locally against Render

```bash
cd frontend
set VITE_API_BASE_URL=https://<service>.onrender.com && npm run dev
```
(`CORS_ORIGINS` on Render must then also include `http://localhost:5173` while you test.)

## 6. Vercel (frontend)

New Project → import the repo → **Root Directory: `frontend`** (framework Vite is detected; `vercel.json` sets headers).
Environment variables (Production):

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<service>.onrender.com` |
| `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | publishable key only |

Then put the final Vercel URL into Render's `CORS_ORIGINS` and redeploy the backend.

## 7. End-to-end check (production)

Open the Vercel URL → you land on `/login` → log in → ask in English, Tamil and Tanglish; send a leaf photo; reload (history comes back from Supabase);
confirm Supabase → Table Editor → `messages` has the rows. Voice shows the "not available on this server" message on the free plan.
