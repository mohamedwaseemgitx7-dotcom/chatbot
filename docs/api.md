# FarmerAssist API

Base URL: `http://127.0.0.1:8000` locally, `https://<service>.onrender.com` in production. All errors are JSON
`{"detail": "..."}` — never stack traces. Every response carries `X-Request-ID`.

| Method | Path | Rate limit | Purpose |
|---|---|---|---|
| GET | `/api/health` | — | Liveness: `{"status":"ok","service":"farmerassist-api"}` |
| GET | `/api/health/ready` | — | Components: database, intent/embedding models, knowledge record count, vision model, voice |
| POST | `/api/auth/login` | 5/min | `{"username","password"}` → `{"token","expires_at","username"}`; wrong → **401**; not configured → **503** |
| GET | `/api/auth/me` | — | Current user (Bearer token) |
| POST | `/api/auth/logout` | — | Revokes the token |
| POST | `/api/chat` | 20/min | Agriculture Q&A in English / Tamil / Tanglish |
| POST | `/api/image/analyze` | 5/min | Preliminary crop-leaf analysis |
| POST | `/api/voice/transcribe` | 5/min | Speech → text (503 when voice is disabled on the server) |

`/api/chat`, `/api/image/analyze` and `/api/voice/transcribe` require `Authorization: Bearer <token>` from
`/api/auth/login`; missing/expired/revoked token → **401** `{"detail":"Please log in again."}`. Tokens are
HMAC-SHA256 signed with `SESSION_SECRET`, expire after `SESSION_TTL_HOURS` (12), and revocation is in-memory
(a server restart forgets logouts, but tokens still expire). One account only (`DEMO_USERNAME` / `DEMO_PASSWORD_HASH`).

Image responses also carry `model_name`, `model_version` and `dataset_version`, so every stored prediction can be
traced to the exact model build.

Exceeding a limit returns **429** `{"detail":"Too many requests. Please wait a moment and try again."}` with `Retry-After`.

## POST /api/chat

```json
{ "message": "paddy la brown spot vandhuruchu enna pannanum", "conversation_id": "7c1e…uuid (optional)", "language": "tanglish (optional hint)" }
```
`message`: 1–1000 characters (whitespace-only rejected). `conversation_id`: UUID. Invalid input → **422**
`{"detail":"Invalid request.","errors":[{"field":"message","reason":"…"}]}` (submitted values are not echoed).

```json
{
  "language": "tanglish",
  "intent": "leaf_spot",
  "confidence": 0.985,
  "status": "answered",
  "crop": "paddy",
  "response": "…verbatim excerpt of the official record…",
  "sources": [{ "title": "…", "url": "https://agritech.tnau.ac.in/…", "publisher": "TNAU Agritech Portal",
                "retrieved_at": "2026-09-24T…", "verification_status": "official_source_pending_review" }],
  "conversation_id": "7c1e…"
}
```
`status`: `answered` (from verified knowledge, always with sources) · `no_knowledge` · `clarification` · `out_of_domain`
· `conversational` (greeting/thanks) · `guidance` (price/weather/scheme pointers to official portals) · `unavailable`.

## POST /api/image/analyze

`multipart/form-data`: `file` (JPEG/PNG/WEBP ≤ 5 MB — checked by content, not name), optional `conversation_id`.
Non-images → **400**, too large → **413**.

```json
{ "status": "ok", "crop": "paddy", "prediction": "Brown spot", "healthy": false, "confidence": 0.94,
  "top_predictions": [{ "crop": "paddy", "condition": "Brown spot", "confidence": 0.94 }],
  "possible_causes": ["Fungal leaf spot (Bipolaris oryzae)"], "recommended_next_steps": ["…official excerpt…"],
  "sources": [ … ], "disclaimer": "This is a preliminary AI prediction …", "model_version": "mnv3s-…" }
```
`status: "uncertain"` (with `reason`: `unsupported` · `low_confidence` · `not_plant` · `too_small` · `too_dark` ·
`too_bright` · `too_blurry`) and `status: "model_unavailable"` carry only a `message` — no crop or prediction is ever guessed.

## POST /api/voice/transcribe

`multipart/form-data`: `audio` (WebM/Ogg/MP4/WAV/MP3 ≤ 10 MB, ≤ 60 s).

```json
{ "text": "நெல்லுக்கு எந்த உரம் போட வேண்டும்?", "detected_language": "tamil", "whisper_language": "ta",
  "language_probability": 0.97, "duration_seconds": 2.4 }
```
The client sends `text` to `/api/chat`. Disabled server → **503** `{"detail":"Voice input isn't available on this server."}`.
