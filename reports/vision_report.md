# Vision model report — mnv3s-20260924-1120 (dataset vision-2026.09.2)

- test accuracy 0.9614 · macro-F1 0.9535 · images 2852
- field_datasets: accuracy 0.9775 · macro-F1 0.9623 · images 1157
- plantvillage_lab: accuracy 0.9871 · macro-F1 0.9837 · images 1471
- plantdoc_field_web: accuracy 0.7098 · macro-F1 0.6894 · images 224
- at threshold 0.6: answers 96% of supported-class photos, accuracy when answering 0.9862
- unseen crops rejected: 0.765 ({'plantvillage_lab': {'images': 301, 'rejection_rate': 0.8771}, 'plantdoc_field_web': {'images': 299, 'rejection_rate': 0.6522}})
- quality gates passed: True · weak classes: none

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| rice_healthy | 0.974 | 1.0 | 0.987 | 37 |
| rice_brown_spot | 1.0 | 0.981 | 0.99 | 207 |
| rice_bacterial_leaf_blight | 0.969 | 0.996 | 0.982 | 223 |
| rice_leaf_blast | 1.0 | 1.0 | 1.0 | 136 |
| tomato_healthy | 0.983 | 0.978 | 0.98 | 230 |
| tomato_early_blight | 0.931 | 0.919 | 0.925 | 161 |
| tomato_late_blight | 0.979 | 0.979 | 0.979 | 233 |
| tomato_leaf_mold | 0.966 | 0.947 | 0.957 | 152 |
| tomato_septoria_leaf_spot | 0.949 | 0.961 | 0.955 | 232 |
| chilli_healthy | 0.984 | 0.992 | 0.988 | 128 |
| chilli_leaf_curl | 0.993 | 0.987 | 0.99 | 153 |
| banana_healthy | 0.733 | 0.957 | 0.83 | 23 |
| banana_leaf_disease | 0.935 | 0.915 | 0.925 | 47 |
| maize_healthy | 1.0 | 1.0 | 1.0 | 170 |
| maize_common_rust | 0.98 | 0.949 | 0.965 | 158 |
| maize_northern_leaf_blight | 0.938 | 0.927 | 0.932 | 178 |
| maize_gray_leaf_spot | 0.821 | 0.897 | 0.857 | 87 |
| unsupported | 0.931 | 0.909 | 0.92 | 297 |
