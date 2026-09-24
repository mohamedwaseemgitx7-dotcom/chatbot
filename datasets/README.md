# FarmerAssist Datasets (v0.1, built 2026-09-23)

Multilingual (English / Tamil / Tanglish) dataset package for a local-first, agriculture-only chatbot:
intent classification, Tanglish normalisation, a small RAG knowledge base, controlled response templates,
and metadata for image and voice evaluation. Designed for TF-IDF + Logistic Regression, sentence-transformer
retrieval with NumPy cosine similarity, MobileNetV3-Small and Whisper on an 8 GB laptop.

**Status: prototype training data, not production-ready.** See *Validation* and *Limitations*.

## Folder layout

| Path | Purpose |
|---|---|
| `nlp/farmer_queries.csv` / `.jsonl` | Main intent-classification dataset (3547 rows, with split) |
| `nlp/intent_examples.csv` | Clean positive + negative (confusable) examples per intent (1536 rows) |
| `nlp/intents.json` | 50 intents: description, examples, related crops, keywords, negatives |
| `nlp/spelling_variations.csv` | Clean → noisy pairs (3622 rows) |
| `nlp/out_of_domain_queries.csv` | Non-agriculture queries the bot must refuse (219 rows) |
| `nlp/weather_queries.csv` | Weather / rain / drought / heat queries (subset of farmer_queries) |
| `nlp/tamil_normalization.json` | Tamil-script → English token map (NLP only; never shown in UI) |
| `tanglish/tanglish_dictionary.json` | 505 terms with Tamil, spelling variants, English, category, plus a flat lookup |
| `knowledge/agricultural_knowledge.csv` / `.json` | RAG knowledge base (419 records) |
| `knowledge/crops, diseases, pests, fertilizers, pesticides, irrigation, soil, schemes .csv` | Structured tables |
| `vision/` | Licensed crop-leaf image dataset: metadata (manifest, classes, sources, licences, report) — see `vision/README.md` and `vision/SOURCES.md` |
| `voice/voice_queries.csv` | 360 recording prompts / references for Whisper evaluation (no audio yet) |
| `responses/response_templates.json` | 129 templates (type × EN/TA/Tanglish) |
| `reports/` | validation report, leakage log, baseline model results |
| `tools/` | the generator source used to create this package |

## farmer_queries.csv columns

`id` · `text` (what the farmer typed) · `language` (english / tamil / tanglish / mixed) · `script` (latin / tamil / mixed) ·
`intent` · `crop` (entity; empty when not mentioned) · `topic` (coarse group) · `normalized_text` (dictionary-based
normalisation for the NLP pipeline) · `difficulty` (easy = clean, medium = light noise, hard = short/voice/mixed) ·
`noise_type` · `expected_response_type` (template family) · `response_id` (knowledge record `KB_*` or template `TPL_*`) ·
`group_id` (all variants of one seed sentence) · `split`.

**Design change from the brief:** crop names (paddy, tomato…) are an **entity column, not intents**, and
fungal / bacterial / viral are **attributes in `diseases.csv`**, not intents — farmers describe symptoms, not pathogen types.
This keeps the classifier from learning crop names instead of problems.

## Distribution

Languages: English 28.5% · Tamil 31.8% · Tanglish 32.2% · Mixed 7.5%
(the brief's 33/33/34 target is met if mixed rows are counted with their base language).

Crop rows: paddy 127, sugarcane 128, drumstick 128, maize 129, coconut 129, groundnut 129, turmeric 134, banana 136, greengram 142, blackgram 150, onion 151, cotton 155, brinjal 166, chilli 196, tomato 211.

| Intent | Rows |
|---|---|
| agri_general_info | 43 |
| aphids | 79 |
| bollworm | 43 |
| crop_disease | 82 |
| crop_insurance | 57 |
| drip_irrigation | 60 |
| drought | 71 |
| farm_machinery | 43 |
| fertilizer | 79 |
| fertilizer_timing | 60 |
| fruit_borer | 82 |
| fruit_rot | 79 |
| government_scheme | 43 |
| greeting | 42 |
| harvesting | 82 |
| heat_stress | 82 |
| image_upload_help | 43 |
| irrigation | 87 |
| leaf_blight | 82 |
| leaf_curl | 82 |
| leaf_folder | 43 |
| leaf_spot | 74 |
| market_price | 90 |
| micronutrient_deficiency | 71 |
| nitrogen_deficiency | 82 |
| organic_farming | 57 |
| organic_fertilizer | 63 |
| out_of_domain | 291 |
| pest_attack | 79 |
| phosphorus_deficiency | 74 |
| pm_kisan | 43 |
| post_harvest_storage | 87 |
| potassium_deficiency | 71 |
| rain_damage | 79 |
| root_rot | 74 |
| seed_selection | 90 |
| seed_treatment | 60 |
| soil_health | 43 |
| soil_ph | 43 |
| soil_testing | 43 |
| sowing_time | 90 |
| stem_borer | 71 |
| subsidy | 43 |
| thanks | 43 |
| thrips_mites | 90 |
| water_shortage | 57 |
| weather | 43 |
| whitefly | 74 |
| wilting | 87 |
| yellow_leaf | 71 |

## Split (70/15/15, group-aware)

Train 2582 · Validation 468 · Test 497.
Splitting is done **by seed group per intent**, so a sentence and its spelling / phonetic / crop variants never
appear on both sides. A char n-gram TF-IDF check then flagged 38 near-duplicate
evaluation rows (cosine ≥ 0.90 to a train row from another group); those groups were moved to train, leaving
0 (`reports/leakage_candidates_before_fix.csv`).

## Generation method

1. **Hand-written seeds**: 4–5 natural farmer phrasings per intent per language (≈640 total), with a `{c}` crop slot.
2. **Crop filling** with language-appropriate names and Tanglish spelling variants (nel / nellu / nelu).
3. **Noise**: spelling errors (Latin typos; dropped pulli or ழ/ள, ண/ன, ற/ர swaps in Tamil), phonetic Tanglish
   variants from the dictionary, short keyword queries (domain words only), missing non-domain words, farmer
   address words (sir / anna / ஐயா), code-mixing, and simulated ASR errors (homophones, merged words).
4. **Cleaning**: exact de-duplication after normalisation (0 duplicates remain), label-value validation,
   leakage check, dangling `response_id` check (0).

## Knowledge verification

Every knowledge row has `verification_required = true`. Content is general agronomy of the kind published by
TNAU / ICAR; it was written for this project, not copied from a single source, and **contains no pesticide or
fertilizer doses, no withdrawal periods and no chemical product recommendations** — those always point to the
agriculture officer / KVK. Scheme rows show `last_verified`: PM-KISAN amount, Kuruvai package extension,
paddy procurement incentive, free power, crop-loan target and seed subsidy were checked against 2026 news and
budget reports on the build date; all other scheme rows say "not re-verified in this build".

## Images

Built by `scripts/vision/build_dataset.py` from licensed sources only (CC0 1.0 / CC BY 4.0) — see
[vision/README.md](vision/README.md). Never add generated images or photos from search engines / social media.

## Voice

`voice_queries.csv` lists what each speaker should say (`transcript`), the planned `audio_path`, target noise level,
speaking style and a normalised `expected_text` for WER. `recording_status` is `not_recorded` for all rows.
Whisper usually outputs Tamil script or English for spoken Tanglish, so compare Tanglish results after
transliteration or at the intent level.

## Validation

| Check | Result |
|---|---|
| Total rows (farmer_queries) | 3547 |
| Intents | 50 (incl. out_of_domain) |
| Crops / diseases / pests | 15 / 39 / 40 |
| Tanglish terms | 505 |
| Out-of-domain rows | 291 in farmer_queries, 219 in its own file |
| Duplicates | 0 |
| Potential leakage | 38 before fix → 0 after |
| Missing required values | 0 |
| Invalid label values | 0 |

**Baseline model** (char+word TF-IDF + Logistic Regression, trained on train only):
validation accuracy 0.643, **test accuracy 0.602, macro-F1 0.566**,
out-of-domain recall 0.766. Weakest test intents: drought (0.0), greeting (0.0), fruit_rot (0.0), fertilizer_timing (0.0), post_harvest_storage (0.0), potassium_deficiency (0.0), weather (0.0), seed_selection (0.11).

This number is low **because the split is honest**: each intent has only ~13 seed phrasings, so test rows are
genuinely new wordings. It tells you exactly where to add data.

## What needs more data (from the report)

- **Intents**: every intent needs more distinct seed phrasings (aim for 30+ per intent per language), starting with
  the weakest test intents above and the look-alike groups (fertilizer vs deficiencies, leaf_blight vs potassium
  deficiency, drought vs water_shortage vs wilting).
- **Crops**: drumstick, turmeric, groundnut and sugarcane have the fewest rows; paddy is under-represented given
  its importance in the delta.
- **Language**: English is slightly below target; Tamil knowledge records (54) and Tanglish (54) are far fewer than
  English (311) — disease and pest records exist only in English, so answers for those rely on templates or
  cross-lingual retrieval.
- **Knowledge base**: 419 records, below the 500 target. Add Tamil/Tanglish versions of disease, pest and
  harvest records, and have an agronomist review everything.
- **External verification needed**: all of `knowledge/`, especially `schemes.csv`, `diseases.csv` management text,
  and the seasons in `crops.csv`.
- **Synthetic fields**: every query text, noise variant, voice transcript and difficulty label is synthetic;
  images and audio do not exist yet.

## Licensing

Generated text and tables: free to use in your project (suggest CC BY 4.0 for your release). Images and audio you
add later keep their own licences — record them in the manifest.

## Future expansion

Collect real farmer queries (Kisan Call Centre open data, your own users) and relabel; add allied sectors
(livestock, fisheries — currently `borderline_allied` out-of-domain); add more crops (mango, tapioca, millets);
record voice with multiple speakers and districts; train and compare a multilingual sentence-embedding classifier.
