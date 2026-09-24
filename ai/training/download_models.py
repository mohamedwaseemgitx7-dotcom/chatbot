"""
Downloads the pre-trained sentence-embedding model used at runtime (offline step).

    backend/.venv/Scripts/python ai/training/download_models.py

sentence-transformers/all-MiniLM-L6-v2 (Apache-2.0), int8-quantised ONNX export for AVX2 CPUs (~23 MB).
It runs on onnxruntime + tokenizers, so the API doesn't need PyTorch (fits Render's 512 MB instance).
"""
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "main"
FILES = {"onnx/model_quint8_avx2.onnx": "model.onnx", "tokenizer.json": "tokenizer.json", "LICENSE": None, "README.md": "MODEL_CARD.md"}
OUT = Path(__file__).resolve().parents[2] / "backend" / "models" / "embedding"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for remote, local in FILES.items():
        if local is None:
            continue
        path = hf_hub_download(REPO, remote, revision=REVISION)
        shutil.copyfile(path, OUT / local)
        print(f"{remote} -> {(OUT / local).relative_to(OUT.parents[2])} ({(OUT / local).stat().st_size // 1024} KB)")
    (OUT / "SOURCE.txt").write_text(f"{REPO} ({REVISION}) — Apache-2.0 — onnx/model_quint8_avx2.onnx\n", encoding="utf-8")


if __name__ == "__main__":
    main()
