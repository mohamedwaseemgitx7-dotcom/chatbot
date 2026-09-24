# Vision dataset report (vision-2026.09.2)

- images: 19372 · classes: 18 · splits: {'train': 13111, 'validation': 2809, 'test': 2852, 'ood_test': 600}
- exact duplicates removed: 1452 · near-duplicate pairs grouped: 16936
- label-conflict groups dropped: 360
- train↔test leakage: 0 · train↔validation leakage: 0

| label | train | validation | test | ood_test |
|---|---|---|---|---|
| banana_healthy | 108 | 23 | 23 | 0 |
| banana_leaf_disease | 223 | 48 | 47 | 0 |
| chilli_healthy | 601 | 129 | 128 | 0 |
| chilli_leaf_curl | 724 | 156 | 153 | 0 |
| maize_common_rust | 698 | 150 | 158 | 0 |
| maize_gray_leaf_spot | 397 | 85 | 87 | 0 |
| maize_healthy | 796 | 170 | 170 | 0 |
| maize_northern_leaf_blight | 792 | 170 | 178 | 0 |
| ood_test | 0 | 0 | 0 | 600 |
| rice_bacterial_leaf_blight | 1052 | 225 | 223 | 0 |
| rice_brown_spot | 969 | 207 | 207 | 0 |
| rice_healthy | 176 | 38 | 37 | 0 |
| rice_leaf_blast | 636 | 136 | 136 | 0 |
| tomato_early_blight | 715 | 153 | 161 | 0 |
| tomato_healthy | 1046 | 224 | 230 | 0 |
| tomato_late_blight | 1044 | 223 | 233 | 0 |
| tomato_leaf_mold | 687 | 148 | 152 | 0 |
| tomato_septoria_leaf_spot | 1044 | 224 | 232 | 0 |
| unsupported | 1403 | 300 | 297 | 0 |

| source | train | validation | test | ood_test |
|---|---|---|---|---|
| banana_mendeley | 551 | 118 | 116 | 0 |
| chilli_mendeley | 1325 | 285 | 281 | 0 |
| plantdoc | 765 | 163 | 224 | 299 |
| plantvillage | 6896 | 1478 | 1471 | 301 |
| rice_samples | 2703 | 579 | 575 | 0 |
| riceleafbd | 871 | 186 | 185 | 0 |
