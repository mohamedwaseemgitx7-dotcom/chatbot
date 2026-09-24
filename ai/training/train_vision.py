"""
Fine-tunes MobileNetV3-Small on the licensed crop-leaf dataset and exports it to ONNX (offline step).

    ai/.venv-train/Scripts/python ai/training/train_vision.py     (CUDA PyTorch training environment)

Transfer learning: ImageNet weights → new 10-class head. Phase 1 trains the head, phase 2 fine-tunes the
whole network. The best epoch is chosen on the validation split; the test split is evaluated once.
Outputs: backend/models/vision/crop_disease.onnx + labels.json (classes + model card), reports/vision_report.json
"""
import csv
import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "datasets" / "vision" / "image_dataset_manifest.csv"
CLASSES_CSV = ROOT / "datasets" / "vision" / "image_classes.csv"
OUT = ROOT / "backend" / "models" / "vision"
REPORTS = ROOT / "reports"
SEED = 42
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

TRAIN_TF = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.6, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(20),
    transforms.ColorJitter(0.3, 0.3, 0.3, 0.03),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])
EVAL_TF = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(), transforms.Normalize(MEAN, STD)])


class Images(Dataset):
    def __init__(self, rows, labels, transform):
        self.rows, self.index, self.transform = rows, {l: i for i, l in enumerate(labels)}, transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        row = self.rows[i]
        image = Image.open(ROOT / row["image_path"]).convert("RGB")
        return self.transform(image), self.index[row["label"]]


def evaluate(model, loader, device):
    model.eval()
    preds, golds = [], []
    with torch.no_grad():
        for x, y in loader:
            preds.append(model(x.to(device)).argmax(1).cpu())
            golds.append(y)
    p, g = torch.cat(preds).numpy(), torch.cat(golds).numpy()
    return p, g, float((p == g).mean())


def run_epochs(model, loaders, device, params, epochs, lr, tag, best):
    optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)
    for epoch in range(epochs):
        model.train()
        started, total = time.time(), 0.0
        for x, y in loaders["train"]:
            optimizer.zero_grad()
            loss = loss_fn(model(x.to(device)), y.to(device))
            loss.backward()
            optimizer.step()
            total += loss.item()
        scheduler.step()
        _, _, val_acc = evaluate(model, loaders["validation"], device)
        print(f"  {tag} epoch {epoch + 1}/{epochs}  loss {total / len(loaders['train']):.3f}  val acc {val_acc:.3f}  ({time.time() - started:.0f}s)", flush=True)
        if val_acc > best["acc"]:
            best.update(acc=val_acc, state={k: v.detach().clone() for k, v in model.state_dict().items()}, epoch=f"{tag}{epoch + 1}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", device, torch.cuda.get_device_name(0) if device == "cuda" else "")

    with open(CLASSES_CSV, encoding="utf-8-sig") as f:
        class_rows = list(csv.DictReader(f))
    labels = [r["class_name"] for r in class_rows] + ["unsupported"]  # other crops / uncovered diseases
    with open(MANIFEST, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    splits = defaultdict(list)
    for r in rows:
        splits[r["split"]].append(r)
    print({s: len(v) for s, v in splits.items()})
    ood_rows = splits.pop("ood_test", [])  # never trained on — rejection test only

    # Balance classes (banana has far fewer photos than tomato/chilli).
    counts = Counter(r["label"] for r in splits["train"])
    weights = [1.0 / counts[r["label"]] for r in splits["train"]]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
    # Windows DataLoader workers share memory through the page file; 2 workers keep an 8–16 GB laptop stable.
    workers = 2
    loaders = {
        "train": DataLoader(Images(splits["train"], labels, TRAIN_TF), batch_size=48, sampler=sampler, num_workers=workers, persistent_workers=True),
        "validation": DataLoader(Images(splits["validation"], labels, EVAL_TF), batch_size=96, num_workers=workers, persistent_workers=True),
        "test": DataLoader(Images(splits["test"], labels, EVAL_TF), batch_size=96, num_workers=0),
    }

    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(labels))
    model.to(device)

    best = {"acc": -1.0}
    for p in model.features.parameters():
        p.requires_grad = False
    run_epochs(model, loaders, device, model.classifier.parameters(), 4, 2e-3, "head", best)
    for p in model.features.parameters():
        p.requires_grad = True
    run_epochs(model, loaders, device, model.parameters(), 12, 4e-4, "fine", best)

    model.load_state_dict(best["state"])
    OUT.mkdir(parents=True, exist_ok=True)
    torch.save(best["state"], ROOT / "ai" / "models" / "vision" / "best_state.pt")  # checkpoint before the final test
    del loaders["train"], loaders["validation"]  # release worker processes before testing
    pred, gold, test_acc = evaluate(model, loaders["test"], device)
    per_class = {labels[i]: round(float((pred[gold == i] == i).mean()), 3) for i in range(len(labels)) if (gold == i).any()}
    confusion = Counter((labels[g], labels[p]) for g, p in zip(gold, pred) if g != p)

    # Unseen crops (potato, pepper, strawberry, soybean, raspberry): share rejected as "unsupported"
    # or left below the serving confidence threshold (0.60) — i.e. NOT given a crop/disease answer.
    ood_loader = DataLoader(Images(ood_rows, labels, EVAL_TF), batch_size=96, num_workers=0)
    model.eval()
    probs = []
    with torch.no_grad():
        for x, _ in ood_loader:
            probs.append(torch.softmax(model(x.to(device)), 1).cpu())
    probs = torch.cat(probs) if probs else torch.zeros((0, len(labels)))
    unsupported_index = labels.index("unsupported")
    rejected = [(p.argmax().item() == unsupported_index) or (p.max().item() < 0.60) for p in probs]
    ood_rejection = float(np.mean(rejected)) if rejected else None
    print(f"unseen-crop rejection rate: {ood_rejection}")
    print(f"best epoch {best['epoch']}  val acc {best['acc']:.3f}  TEST acc {test_acc:.3f}")

    OUT.mkdir(parents=True, exist_ok=True)
    model.eval().cpu()
    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(model, dummy, OUT / "crop_disease.onnx", input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False)

    # The exported graph must match PyTorch before it is shipped.
    import onnxruntime as ort
    session = ort.InferenceSession(str(OUT / "crop_disease.onnx"), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        reference = model(dummy).numpy()
    max_diff = float(np.abs(session.run(None, {"image": dummy.numpy()})[0] - reference).max())
    print(f"ONNX vs PyTorch max |diff| = {max_diff:.2e}")
    assert max_diff < 1e-3, "ONNX export does not match the PyTorch model"

    card = {
        "version": datetime.now(timezone.utc).strftime("mnv3s-%Y%m%d"),
        "architecture": "MobileNetV3-Small (ImageNet-pretrained, fine-tuned)",
        "input": "RGB 224x224, resize 256 + centre crop, ImageNet mean/std",
        "classes": [{"name": r["class_name"], "crop": r["crop"], "condition": r["disease"],
                     "healthy": r["disease"].strip().lower() == "healthy", "cause": r["description"]} for r in class_rows]
                   + [{"name": "unsupported", "crop": None, "condition": "unsupported", "healthy": False, "cause": None}],
        "unseen_crop_rejection_rate": round(ood_rejection, 4) if ood_rejection is not None else None,
        "datasets": sorted({(r["source"].split(":")[0], r["license"]) for r in rows}),
        "test_accuracy": round(test_acc, 4),
        "validation_accuracy": round(best["acc"], 4),
        "per_class_test_accuracy": per_class,
        "limitations": [
            "Tomato images are PlantVillage lab photos (plain background); field photos may be recognised less reliably.",
            "Each crop comes from a different dataset, so crop identification partly relies on photo style.",
            "Banana has only ~470 photos; its accuracy estimate is less certain.",
            "Only these 10 classes are supported; anything else must be reported as uncertain, never forced.",
            "Rejection of unsupported plants is learned from other PlantVillage crops and two uncovered diseases; "
            "field photos of other crops may still be misread — see unseen_crop_rejection_rate.",
        ],
    }
    (OUT / "labels.json").write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "vision_report.json").write_text(json.dumps({
        **{k: card[k] for k in ("version", "test_accuracy", "validation_accuracy", "per_class_test_accuracy",
                                "unseen_crop_rejection_rate", "datasets", "limitations")},
        "unseen_crop_test_images": len(ood_rows),
        "best_epoch": best["epoch"], "test_images": int(len(gold)),
        "most_common_confusions": [{"true": a, "predicted": b, "count": n} for (a, b), n in confusion.most_common(8)],
        "onnx_max_abs_diff": max_diff, "device": device,
    }, indent=2), encoding="utf-8")
    print(json.dumps(per_class, indent=1))


if __name__ == "__main__":
    main()
