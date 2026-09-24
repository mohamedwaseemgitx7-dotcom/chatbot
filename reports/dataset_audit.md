# Dataset audit

- farmer_queries: 3547 rows, 50 intents, languages {'english': 28.5, 'tamil': 31.8, 'tanglish': 32.2, 'mixed': 7.5}
- missing values: {'id': 0, 'text': 0, 'language': 0, 'intent': 0, 'split': 0}
- exact duplicates (same label): 0; same text with conflicting labels: 0
- unknown intent labels: none
- script/language mismatches: 0
- eval rows nearly identical (cos ≥ 0.95) to a train row: 0
- smallest intents: {'greeting': 42, 'thanks': 43, 'agri_general_info': 43, 'soil_testing': 43, 'bollworm': 43, 'soil_health': 43, 'leaf_folder': 43, 'weather': 43}

- dataset-package knowledge: 419 records, source types {'curated_general_agronomy': 402, 'scheme_summary_from_official_sources': 17}, 0 with source URL → not served
- official-source knowledge (served): 0 records, {}
- other: {'out_of_domain_rows': 219, 'out_of_domain_categories': {'general_knowledge': 14, 'politics': 13, 'sports': 13, 'movies': 13, 'shopping': 13, 'finance': 13, 'entertainment': 13, 'coding': 12, 'technology': 12, 'celebrity': 11, 'human_health': 11, 'recipes': 11}, 'tanglish_terms': 505, 'image_manifest_rows': 7233, 'voice_metadata_rows_(no_audio)': 360}
