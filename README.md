# 🌾 FarmerAssist — agriculture assistant for Tamil Nadu farmers

Ask farming questions in **English, Tamil or Tanglish**, send a **leaf photo**, or **speak** — FarmerAssist answers in the
same language, only about agriculture, and only from **official sources** (with the source link shown).
No paid LLM API: every model runs locally / on the server.

> ⚠️ Answers are preliminary guidance. Knowledge comes from the TNAU Agritech Portal and is marked
> *"official source, pending expert review"*; photo results are AI predictions, not diagnoses. Farmers should confirm
> products and doses with their local agriculture officer.

## How it answers

```
text / voice ─► language detection (Tamil · Tanglish · English · mixed)
             ─► Tamil/Tanglish → English normalisation (lexicons, ASR-error tolerant)   ← original text is never changed in the UI
             ─► crop detection ─► MiniLM sentence embedding (ONNX)
             ─► intent classifier (char+word TF-IDF + embedding → logistic regression)
             ─► domain guard (classifier + farming vocabulary + crop) → refuse / clarify / answer
             ─► retrieval over verified knowledge (NumPy cosine, crop/topic aware, similarity threshold)
             ─► controlled response: fixed templates + verbatim excerpts + sources (no free text generation)

photo ─► content check (JPEG/PNG/WEBP ≤ 5 MB) ─► OpenCV decode + quality checks
      ─► MobileNetV3-Small (ONNX, 10 classes + "unsupported") ─► confidence gate ─► knowledge for the condition
voice ─► faster-whisper (Tamil/English) ─► transcript ─► same chat pipeline
```

Nothing invents facts: if no verified record clears the threshold the bot says
*"I don't have enough verified information to answer that safely…"*.

## Repository

```
frontend/            React + Vite chat UI (Supabase client for history; calls the API for AI)
backend/app/         FastAPI: api/routes, services, nlp, embeddings, rag, vision, voice, security, database
backend/models/      runtime artifacts: intent/, embedding/ (MiniLM int8 ONNX), vision/ (ONNX + model card),
                     knowledge/ (verified records + embeddings), lexicon/
datasets/            NLP training data, Tanglish/Tamil lexicons, vision manifest (licences per image)
data/                knowledge pipeline: sources/ → raw/ (git-ignored) → processed/ → verified/
scripts/             collect_sources → clean_knowledge → deduplicate → validate_knowledge → build_knowledge_index → import_supabase
ai/                  offline training: train_intent.py, train_vision.py, download_models.py, vision/, voice/
supabase/migrations/ schema, RLS, storage buckets, knowledge provenance
tests/               pytest suite (chat, language, intent, RAG, image, voice, security, rate limit, health, Supabase)
reports/             intent_report.json, vision_report.json, dataset_audit.md
docs/DEPLOYMENT.md   Supabase → Render → Vercel, step by step
```

## Run locally

```bash
# backend
cd backend
python -m venv .venv && .venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pip install -r requirements-voice.txt      # optional: voice (set VOICE_ENABLED=true)
copy .env.example .env                                    # fill in Supabase values
.venv\Scripts\python run.py                               # http://127.0.0.1:8000/api/health/ready

# frontend
cd frontend && npm install && copy .env.example .env && npm run dev   # http://localhost:5173

# tests
backend\.venv\Scripts\python -m pytest
```

## Rebuilding the AI assets (offline — never during requests)

```bash
backend\.venv\Scripts\python ai\training\download_models.py        # MiniLM ONNX embedding model
backend\.venv\Scripts\python ai\training\train_intent.py           # intent classifier + reports/intent_report.json
backend\.venv\Scripts\python scripts\collect_sources.py targeted   # official pages (robots.txt respected, 2 s delay)
backend\.venv\Scripts\python scripts\collect_sources.py fetch
backend\.venv\Scripts\python scripts\clean_knowledge.py && backend\.venv\Scripts\python scripts\deduplicate.py
backend\.venv\Scripts\python scripts\validate_knowledge.py && backend\.venv\Scripts\python scripts\build_knowledge_index.py
backend\.venv\Scripts\python ai\vision\download_datasets.py && backend\.venv\Scripts\python ai\vision\prepare_dataset.py
ai\.venv-train\Scripts\python ai\training\train_vision.py          # CUDA PyTorch env; exports ONNX
```

## Deployment

Frontend on **Vercel**, API on **Render** (free plan: 512 MB — chat, RAG and photo analysis fit in ~270 MB; voice is
disabled there), database and storage on **Supabase**. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and
[SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md).

## Data sources & licences

- Knowledge: TNAU Agritech Portal (Tamil Nadu Agricultural University), collected politely with attribution; each record
  stores its URL and retrieval date. Ask TNAU for permission before any commercial use.
- Images: RiceLeafBD (CC BY 4.0), PlantVillage (CC0 1.0), Chilli Leaf Disease Image Dataset (CC BY 4.0),
  Banana Leaf Disease Images (CC BY 4.0) — Mendeley Data; per-image source in `datasets/vision/image_dataset_manifest.csv`.
- Embedding model: sentence-transformers/all-MiniLM-L6-v2 (Apache-2.0). Speech: faster-whisper / OpenAI Whisper (MIT).
