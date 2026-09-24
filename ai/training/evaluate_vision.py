"""
Evaluate the staged vision model and apply the quality gates (offline).

    ai/.venv-train/Scripts/python ai/training/evaluate_vision.py

Reports, separately (a lab-photo score says little about field photos):
  - all test images, PlantVillage (lab), PlantDoc (internet field photos), field datasets (rice/chilli/banana)
  - precision / recall / F1 per class, macro-F1, confusion matrix
  - confidence distribution for correct vs wrong predictions, coverage/accuracy at the serving threshold
  - rejection of crops never trained on (ood_test split), lab vs field
Writes ai/models/vision/staging/evaluation.json, confusion_matrix.csv and reports/vision_report.{json,md}.
"""
import csv
import json
import io
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
from class_metrics import compute_metrics  # noqa: E402
from confusion_matrix import confusion, top_confusions, write_csv  # noqa: E402
from train_vision import CONFIG, ROOT, STAGING, Images, build_model, transforms_for  # noqa: E402

STYLE_GROUP = {"lab": "plantvillage_lab", "field_web": "plantdoc_field_web", "field": "field_datasets"}


def manifest_rows():
    with open(ROOT / CONFIG["data"]["manifest"], encoding="utf-8") as f:
        return list(csv.DictReader(f))


def probabilities(model, items, device):
    loader = DataLoader(Images(items, transforms_for(False)), batch_size=96, num_workers=0)
    out = []
    model.eval()
    with torch.no_grad():
        for x, _ in loader:
            out.append(torch.softmax(model(x.to(device)), 1).cpu())
    return torch.cat(out).numpy() if out else np.zeros((0, 1))


def main():
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    classes = json.loads((STAGING / "classes.json").read_text(encoding="utf-8"))
    labels = [c["name"] for c in classes]
    index = {label: i for i, label in enumerate(labels)}
    model = build_model(len(labels))
    model.load_state_dict(torch.load(STAGING / "model.pt", map_location="cpu"))
    model.to(device)
    threshold = CONFIG["evaluation"]["confidence_threshold"]
    unsupported = index.get("unsupported")

    rows = manifest_rows()
    test = [r for r in rows if r["split"] == "test" and r["label"] in index]
    items = [(ROOT / "datasets" / "vision" / "test" / r["label"] / f"{r['image_id']}.jpg", index[r["label"]]) for r in test]
    probs = probabilities(model, items, device)
    gold = np.array([label for _, label in items])
    pred = probs.argmax(1)
    conf = probs.max(1)

    report: dict[str, Any] = {"test": compute_metrics(gold, pred, labels), "by_source": {}}
    groups = defaultdict(list)
    for i, r in enumerate(test):
        groups[STYLE_GROUP.get(r["image_style"], r["image_style"])].append(i)
    for name, idx in groups.items():
        report["by_source"][name] = {k: v for k, v in compute_metrics(gold[idx], pred[idx], labels).items() if k != "per_class"}

    correct = pred == gold
    bins = np.linspace(0, 1, 11)
    report["confidence_distribution"] = {
        "bins": [round(b, 1) for b in bins[:-1]],
        "correct": np.histogram(conf[correct], bins)[0].tolist(),
        "wrong": np.histogram(conf[~correct], bins)[0].tolist(),
    }
    answered = (conf >= threshold) & (pred != unsupported) if unsupported is not None else conf >= threshold
    known = gold != unsupported if unsupported is not None else np.ones_like(gold, bool)
    report["at_threshold"] = {
        "threshold": threshold,
        "coverage_known_classes": round(float(answered[known].mean()), 4),
        "accuracy_when_answered": round(float(correct[answered & known].mean()), 4) if (answered & known).any() else None,
    }

    ood = [r for r in rows if r["split"] == "ood_test"]
    ood_probs = probabilities(model, [(ROOT / r["file_path"], 0) for r in ood], device)
    rejected = (ood_probs.argmax(1) == unsupported) | (ood_probs.max(1) < threshold) if len(ood) else np.array([])
    report["unseen_crops"] = {"images": len(ood), "rejection_rate": round(float(rejected.mean()), 4) if len(ood) else None, "by_source": {}}
    for style in sorted({r["image_style"] for r in ood}):
        idx = [i for i, r in enumerate(ood) if r["image_style"] == style]
        report["unseen_crops"]["by_source"][STYLE_GROUP.get(style, style)] = {"images": len(idx), "rejection_rate": round(float(rejected[idx].mean()), 4)}

    gates = CONFIG["evaluation"]["quality_gates"]
    weak = {k: v["f1"] for k, v in report["test"]["per_class"].items() if v["f1"] < gates["min_class_f1"]}
    quality_gates: dict[str, Any] = {
        "min_test_macro_f1": {"required": gates["min_test_macro_f1"], "actual": report["test"]["macro_f1"],
                              "pass": report["test"]["macro_f1"] >= gates["min_test_macro_f1"]},
        "min_unseen_crop_rejection": {"required": gates["min_unseen_crop_rejection"], "actual": report["unseen_crops"]["rejection_rate"],
                                      "pass": (report["unseen_crops"]["rejection_rate"] or 0) >= gates["min_unseen_crop_rejection"]},
        "weak_classes_below_min_f1": weak,
    }
    report["quality_gates"] = quality_gates
    report["quality_gates"]["passed"] = all(g["pass"] for g in report["quality_gates"].values() if isinstance(g, dict) and "pass" in g)
    report["top_confusions"] = top_confusions(gold, pred, labels)

    matrix = confusion(gold, pred, labels)
    write_csv(matrix, labels, STAGING / "confusion_matrix.csv")
    (STAGING / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    metadata = json.loads((STAGING / "training_metadata.json").read_text(encoding="utf-8"))
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "vision_report.json").write_text(json.dumps({"model_version": metadata["model_version"],
                                                                      "dataset_version": metadata["dataset_version"], **report}, indent=2), encoding="utf-8")
    md = [f"# Vision model report — {metadata['model_version']} (dataset {metadata['dataset_version']})", "",
          f"- test accuracy {report['test']['accuracy']} · macro-F1 {report['test']['macro_f1']} · images {report['test']['images']}"]
    for name, m in report["by_source"].items():
        md.append(f"- {name}: accuracy {m['accuracy']} · macro-F1 {m['macro_f1']} · images {m['images']}")
    md += [f"- at threshold {threshold}: answers {report['at_threshold']['coverage_known_classes']:.0%} of supported-class photos, "
           f"accuracy when answering {report['at_threshold']['accuracy_when_answered']}",
           f"- unseen crops rejected: {report['unseen_crops']['rejection_rate']} ({report['unseen_crops']['by_source']})",
           f"- quality gates passed: {report['quality_gates']['passed']} · weak classes: {weak or 'none'}", "",
           "| class | precision | recall | F1 | support |", "|---|---|---|---|---|"]
    md += [f"| {k} | {v['precision']} | {v['recall']} | {v['f1']} | {v['support']} |" for k, v in report["test"]["per_class"].items()]
    (ROOT / "reports" / "vision_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
