# Datasets

Full column descriptions: [datasets/README.md](../datasets/README.md). Latest audit: [reports/dataset_audit.md](../reports/dataset_audit.md).

| Data | Used for | Status |
|---|---|---|
| `datasets/nlp/farmer_queries.csv` (+ intent_examples, spelling_variations, out_of_domain_queries, intents.json) | Training the intent classifier | Synthetic farmer phrasings (EN/TA/Tanglish), group-aware 70/15/15 split, audited: 0 duplicates, 0 leakage |
| `datasets/tanglish/tanglish_dictionary.json`, `datasets/nlp/tamil_normalization.json` | Tamil/Tanglish → English normalisation | Copied to `backend/models/lexicon/` at runtime |
| `datasets/knowledge/*` | **Not served.** Generated text with no source URLs | Kept only as a list of candidate topics |
| `data/verified/knowledge.jsonl` | The chatbot's knowledge (RAG) | Verbatim excerpts of TNAU Agritech pages, each with `source_url`, `retrieved_at`, `verification_status` |
| `datasets/vision/image_dataset_manifest.csv` | Training/evaluating the image model | Licensed images (CC BY 4.0 / CC0); per-image source & licence; `ood_test` split = unseen crops |
| `datasets/voice/voice_queries.csv` | Prompts to record for ASR evaluation | Metadata only — no real recordings yet |

## Knowledge pipeline

```
data/sources/sources.json   ← scripts/collect_sources.py targeted   (official crop-protection pages, robots.txt respected)
data/raw/                   ← scripts/collect_sources.py fetch      (git-ignored cache + index.json with retrieval times)
data/processed/             ← clean_knowledge.py (verbatim extraction) → deduplicate.py (exact/near dups, EN↔TA pairing)
data/verified/              ← validate_knowledge.py (every check must pass; rejections listed with reasons)
backend/models/knowledge/   ← build_knowledge_index.py (embeddings)      Supabase `knowledge` ← import_supabase.py
```

Records stay `official_source_pending_review` until an agronomist reviews them; set `verification_status` to
`expert_verified` in `data/verified/knowledge.jsonl` and re-run the last two steps.
