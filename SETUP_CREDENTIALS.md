# FarmerAssist — Supabase & Environment Setup

FarmerAssist needs no OpenAI/Gemini/Claude keys: NLP, RAG and image models run locally.
Supabase (free tier) stores conversations, messages, crop photos, predictions, feedback and rate-limit logs.

## Keys and where they go

| Variable | File | What it is | Browser-safe? |
| :--- | :--- | :--- | :--- |
| `SUPABASE_URL` | `backend/.env` | Project URL, e.g. `https://<ref>.supabase.co` | ✅ |
| `SUPABASE_ANON_KEY` | `backend/.env` | Publishable key (`sb_publishable_…`) | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | **`backend/.env` only** | Secret key (`sb_secret_…`) — bypasses Row Level Security | ❌ **never** |
| `VITE_SUPABASE_URL` | `frontend/.env` | Same project URL | ✅ |
| `VITE_SUPABASE_ANON_KEY` | `frontend/.env` | Same publishable key | ✅ |

Find them in the Supabase Dashboard → **Project Settings → API Keys**.
`.env` files are git-ignored; commit only the `.env.example` templates. The frontend refuses to use a
secret/service-role key if one is put in `frontend/.env` by mistake.

## One-time project setup

1. **Create the schema.** Run `supabase/migrations/20260924000000_initial_schema.sql`:
   - Dashboard → **SQL Editor** → New query → paste the file → **Run**, or
   - with the Supabase CLI: `supabase link --project-ref <ref>` then `supabase db push`.

   It creates the tables (`users`, `conversations`, `messages`, `knowledge`, `image_predictions`,
   `voice_transcriptions`, `feedback`, `rate_limit_logs`), indexes, Row Level Security policies, and two
   **private** Storage buckets: `farmer-images` (JPG/PNG/WEBP, 5 MB) and `farmer-audio` (10 MB).
   Photos are shown through short-lived signed URLs — do **not** make the buckets public.

2. **Enable anonymous sign-ins.** Dashboard → **Authentication → Sign In / Providers** →
   **Allow anonymous sign-ins** → Save. Farmers don't log in yet; each browser silently gets its own
   account so RLS keeps every farmer's chats private. Real login (phone/email) can be linked later.

3. **Fill in the `.env` files** from the table above, then start the app:
   ```bash
   cd backend && python run.py         # http://127.0.0.1:8000
   cd frontend && npm run dev          # http://localhost:5173
   ```

## Check it works

- `GET http://localhost:8000/api/health/ready` → `"database": "connected"`
- Send a message in the app, then look at **Table Editor → conversations / messages** in Supabase.
- If Supabase is unreachable the app keeps working and saves chats on the device; they are uploaded
  when the connection returns.

## Security notes

- Every private table has RLS: a user can only reach their own conversations, messages, predictions,
  voice transcriptions and feedback. Messages can't be edited after they are written.
- `knowledge` is readable by everyone and writable only by the backend (secret key).
- `rate_limit_logs` is backend-only and stores a hash of the IP, never the raw address.
- The backend's secret-key client bypasses RLS, so backend code must check ownership itself
  (`backend/app/database/repositories/conversation_repo.py`).
- Consider enabling CAPTCHA for anonymous sign-ins before a public launch (Authentication → Attack Protection).
