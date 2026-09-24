# FarmerAssist — web UI (React + Vite)

A familiar chat layout (conversation list + chat) with FarmerAssist's own visual identity.
Farmers can ask in Tamil, English or Tanglish, send a crop photo for analysis, or ask by voice.

## Run it

```bash
npm install
npm run dev        # http://localhost:5173 (start the backend first: `python run.py` in ../backend)
npm run build      # production build in dist/
```

Needs Node.js 18+. No UI framework or animation library: plain React + CSS, ~60 KB gzipped JS.

## Configuration (`.env`, see `.env.example`)

| Setting | Default | Meaning |
|---|---|---|
| `VITE_USE_BACKEND` | `true` | `false` = demo mode with local greeting replies, no network calls |
| `VITE_API_URL` | empty | Empty in dev (Vite proxies `/api`); the full backend URL for a production build |
| `BACKEND_PROXY_TARGET` | `http://127.0.0.1:8000` | Where the dev server forwards `/api` |

## Structure

```
src/
├── App.jsx / App.css          header + sidebar (drawer below 900px) + chat
├── styles/tokens.css          design system: colours (light + dark), type, spacing, radii, shadows, motion
├── styles/global.css          resets, buttons, focus ring, spinner, reduced motion
├── hooks/
│   ├── useConversations.js    conversation store, saved to localStorage on this device
│   ├── useAssistant.js        send text / analyse photo / retry, pending states, client rate limit
│   ├── useVoiceRecorder.js    microphone recording (requested only on click, released after)
│   ├── useConnection.js       online/offline + backend health for the header status
│   └── useMediaQuery.js
├── services/
│   ├── botService.js          the only module that calls the backend; normalises every response
│   ├── http.js                fetch/XHR with timeouts → ApiError { kind, status }
│   ├── errors.js              ApiError → farmer-friendly message (400…503, offline, timeout)
│   ├── languageDetector.js    Tamil script / Tanglish word list / English
│   └── rateLimiter.js         token bucket (the server must enforce limits too)
├── utils/                     formatting, image validation (JPG/PNG/WEBP ≤ 5 MB), result labels
└── components/
    ├── AppHeader, Sidebar, ConversationItem, ConfirmDialog
    ├── ChatWindow, MessageList, MessageBubble, PendingReply, WelcomeScreen
    ├── RichText               paragraphs, lists, **bold**, links, ⚠️ warnings — never raw HTML/JSON
    ├── ImageResultCard        crop, possible condition, AI confidence, next steps, disclaimer
    ├── Composer, AttachmentPreview, VoiceBar
    └── Icons                  line icons + FarmerAssist logo
```

## Backend endpoints used

- `POST /api/chat` `{ message, language, conversation_id }` → `{ response, language, conversation_id, … }`
- `POST /api/image/analyze` multipart `file`, `conversation_id` → `{ crop, prediction, confidence, possible_causes, recommended_next_steps, disclaimer }`
- `POST /api/voice/transcribe` multipart `audio` → `{ text, detected_language }`
- `GET /api/health` for the header status

Missing or malformed fields never crash the UI; the user sees a friendly message with Retry where it makes sense.

## Behaviour notes

- Enter sends, Shift+Enter adds a line; sending waits while a Tamil IME is composing.
- Photos: pick, paste or drag-and-drop → preview (name, size, remove) → **Analyze photo** → staged progress → result card labelled "Preliminary AI prediction".
- Voice: record (max 60 s) → stop → transcribing → the text lands in the input to check before sending.
- Conversations are stored only in this browser. Photos are not stored; after a reload the chat shows the file name.
- Dark mode follows the system setting. Reduced-motion preferences are respected.
