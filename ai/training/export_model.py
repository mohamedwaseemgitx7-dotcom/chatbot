"""
Export the evaluated staging model to the API (ONNX) — only if it passed the quality gates.

    ai/.venv-train/Scripts/python ai/training/export_model.py [--force]

Checks evaluation.json gates (use --force only knowingly; the model card records it), exports ONNX, verifies
ONNX output equals PyTorch output, then copies to backend/models/vision/:
  crop_disease.onnx   runtime model (onnxruntime, no PyTorch needed on the server)
  model.pt            PyTorch weights (reference / fine-tuning)
  classes.json, model_config.json, training_metadata.json, evaluation.json, confusion_matrix.csv
  labels.json         runtime model card read by backend/app/vision/classifier.py
"""
import json
import shutil
import sys

import numpy as np
import torch

from train_vision import ROOT, STAGING, build_model

OUT = ROOT / "backend" / "models" / "vision"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    force = "--force" in sys.argv
    evaluation = json.loads((STAGING / "evaluation.json").read_text(encoding="utf-8"))
    if not evaluation["quality_gates"]["passed"] and not force:
        raise SystemExit(f"Quality gates FAILED — not exporting.\n{json.dumps(evaluation['quality_gates'], indent=2)}")

    classes = json.loads((STAGING / "classes.json").read_text(encoding="utf-8"))
    config = json.loads((STAGING / "model_config.json").read_text(encoding="utf-8"))
    metadata = json.loads((STAGING / "training_metadata.json").read_text(encoding="utf-8"))
    model = build_model(len(classes))
    model.load_state_dict(torch.load(STAGING / "model.pt", map_location="cpu"))
    model.eval()

    OUT.mkdir(parents=True, exist_ok=True)
    dummy = torch.randn(1, 3, config["image_size"], config["image_size"])
    torch.onnx.export(model, dummy, OUT / "crop_disease.onnx", input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False)
    import onnxruntime as ort

    session = ort.InferenceSession(str(OUT / "crop_disease.onnx"), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        reference = model(dummy).numpy()
    diff = float(np.abs(session.run(None, {"image": dummy.numpy()})[0] - reference).max())
    if diff > 1e-3:
        raise SystemExit(f"ONNX output differs from PyTorch (max |diff| {diff}) — not exporting")

    for name in ("model.pt", "classes.json", "model_config.json", "training_metadata.json", "evaluation.json", "confusion_matrix.csv"):
        shutil.copyfile(STAGING / name, OUT / name)
    card = {
        "model_name": config["model_name"], "version": metadata["model_version"], "dataset_version": metadata["dataset_version"],
        "architecture": "MobileNetV3-Small (ImageNet-pretrained, fine-tuned)",
        "input": f"RGB {config['image_size']}x{config['image_size']}, resize {config['resize']} + centre crop, ImageNet mean/std",
        "confidence_threshold": config["confidence_threshold"],
        "classes": [{**c, "cause": None} for c in classes],
        "test_accuracy": evaluation["test"]["accuracy"], "test_macro_f1": evaluation["test"]["macro_f1"],
        "by_source": evaluation["by_source"], "unseen_crop_rejection_rate": evaluation["unseen_crops"]["rejection_rate"],
        "quality_gates_passed": evaluation["quality_gates"]["passed"], "exported_with_force": force and not evaluation["quality_gates"]["passed"],
        "onnx_max_abs_diff": diff,
        "limitations": [
            "PlantVillage images are lab photos; field accuracy is reported separately (by_source) and is lower.",
            "Only the listed classes are supported; other crops/diseases should come back as 'unsupported' or low confidence, "
            "but some unseen plants are still misread (see unseen_crop_rejection_rate).",
            "Predictions are preliminary and must be confirmed by an agricultural expert.",
        ],
    }
    (OUT / "labels.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(f"exported {metadata['model_version']} → {OUT.relative_to(ROOT)} (ONNX max |diff| {diff:.1e})")


if __name__ == "__main__":
    main()
