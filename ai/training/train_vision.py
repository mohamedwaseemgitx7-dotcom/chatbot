"""
Train the FarmerAssist crop-leaf classifier (offline, never inside the API).

    ai/.venv-train/Scripts/python ai/training/train_vision.py          (CUDA PyTorch environment, see ai/requirements-train.txt)

Input : datasets/vision/{train,validation}/<label>/*.jpg built by scripts/vision/build_dataset.py
Model : torchvision MobileNetV3-Small, ImageNet-pretrained → new head (phase 1) → full fine-tune (phase 2)
Output: ai/models/vision/staging/{model.pt, classes.json, model_config.json, training_metadata.json}
Next  : evaluate_vision.py (metrics + quality gates) → export_model.py (ONNX, copies to backend/models/vision)
"""
import csv
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load((Path(__file__).parent / "training_config.yaml").read_text(encoding="utf-8"))
STAGING = ROOT / "ai" / "models" / "vision" / "staging"
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def load_classes():
    with open(ROOT / CONFIG["data"]["classes"], encoding="utf-8") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["class_id"]))
    return [{"name": r["label"], "crop": None if r["crop"] == "none" else r["crop"], "condition": r["condition"],
             "healthy": r["condition"].lower() == "healthy"} for r in rows]


def split_items(split, labels):
    base = ROOT / CONFIG["data"]["splits_dir"] / split
    index = {label: i for i, label in enumerate(labels)}
    return [(p, index[p.parent.name]) for p in sorted(base.glob("*/*.jpg")) if p.parent.name in index]


class Noise:
    def __init__(self, p, std):
        self.p, self.std = p, std

    def __call__(self, tensor):
        return (tensor + torch.randn_like(tensor) * self.std).clamp(0, 1) if random.random() < self.p else tensor


def transforms_for(train):
    size, aug = CONFIG["model"]["image_size"], CONFIG["augmentation"]
    if not train:
        return transforms.Compose([transforms.Resize(CONFIG["model"]["resize"]), transforms.CenterCrop(size),
                                   transforms.ToTensor(), transforms.Normalize(MEAN, STD)])
    steps = [transforms.RandomResizedCrop(size, scale=tuple(aug["random_resized_crop_scale"]))]
    if aug["horizontal_flip"]:
        steps.append(transforms.RandomHorizontalFlip())
    if aug["vertical_flip"]:
        steps.append(transforms.RandomVerticalFlip())
    steps += [transforms.RandomRotation(aug["rotation_degrees"]), transforms.ColorJitter(*aug["color_jitter"]),
              transforms.RandomApply([transforms.GaussianBlur(5, sigma=(0.1, 1.5))], p=aug["blur_probability"]),
              transforms.ToTensor(), Noise(aug["noise_probability"], aug["noise_std"]), transforms.Normalize(MEAN, STD)]
    return transforms.Compose(steps)


class Images(Dataset):
    def __init__(self, items, transform):
        self.items, self.transform = items, transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, label = self.items[i]
        with Image.open(path) as img:
            return self.transform(img.convert("RGB")), label


def build_model(num_classes):
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    return model


def predict(model, loader, device):
    model.eval()
    preds, golds = [], []
    with torch.no_grad():
        for x, y in loader:
            preds.append(model(x.to(device)).argmax(1).cpu())
            golds.append(y)
    return torch.cat(golds).numpy(), torch.cat(preds).numpy()


def run_phase(model, loaders, device, params, epochs, lr, tag, best, history):
    cfg = CONFIG["training"]
    optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=cfg["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=cfg["label_smoothing"])
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
        gold, pred = predict(model, loaders["validation"], device)
        macro_f1 = float(f1_score(gold, pred, average="macro"))
        accuracy = float((gold == pred).mean())
        history.append({"epoch": f"{tag}{epoch + 1}", "loss": round(total / len(loaders["train"]), 4),
                        "val_accuracy": round(accuracy, 4), "val_macro_f1": round(macro_f1, 4)})
        print(f"  {tag} {epoch + 1}/{epochs}  loss {history[-1]['loss']:.3f}  val acc {accuracy:.3f}  "
              f"val macro-F1 {macro_f1:.3f}  ({time.time() - started:.0f}s)", flush=True)
        if macro_f1 > best["macro_f1"]:
            best.update(macro_f1=macro_f1, accuracy=accuracy, epoch=f"{tag}{epoch + 1}",
                        state={k: v.detach().cpu().clone() for k, v in model.state_dict().items()})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = CONFIG["training"]
    random.seed(cfg["seed"]); np.random.seed(cfg["seed"]); torch.manual_seed(cfg["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", device, torch.cuda.get_device_name(0) if device == "cuda" else "(CPU — training will be slow)")

    classes = load_classes()
    labels = [c["name"] for c in classes]
    train_items, val_items = split_items("train", labels), split_items("validation", labels)
    print(f"{len(labels)} classes · train {len(train_items)} · validation {len(val_items)}")
    counts = Counter(label for _, label in train_items)
    sampler = WeightedRandomSampler([1.0 / counts[label] for _, label in train_items], num_samples=len(train_items),
                                    replacement=True) if cfg["balanced_sampling"] else None
    workers = CONFIG["data"]["num_workers"]
    loaders = {
        "train": DataLoader(Images(train_items, transforms_for(True)), batch_size=cfg["batch_size"], sampler=sampler,
                            shuffle=sampler is None, num_workers=workers, persistent_workers=workers > 0),
        "validation": DataLoader(Images(val_items, transforms_for(False)), batch_size=96, num_workers=workers,
                                 persistent_workers=workers > 0),
    }

    model = build_model(len(labels)).to(device)
    best, history = {"macro_f1": -1.0}, []
    for p in model.features.parameters():
        p.requires_grad = False
    run_phase(model, loaders, device, model.classifier.parameters(), cfg["head_epochs"], cfg["head_lr"], "head", best, history)
    for p in model.features.parameters():
        p.requires_grad = True
    run_phase(model, loaders, device, model.parameters(), cfg["finetune_epochs"], cfg["finetune_lr"], "fine", best, history)

    STAGING.mkdir(parents=True, exist_ok=True)
    torch.save(best["state"], STAGING / "model.pt")
    dataset_report = json.loads((ROOT / "datasets" / "vision" / "metadata" / "dataset_report.json").read_text(encoding="utf-8"))
    version = datetime.now(timezone.utc).strftime("mnv3s-%Y%m%d-%H%M")
    (STAGING / "classes.json").write_text(json.dumps(classes, indent=2), encoding="utf-8")
    (STAGING / "model_config.json").write_text(json.dumps({
        "model_name": CONFIG["model"]["name"], "architecture": CONFIG["model"]["architecture"],
        "image_size": CONFIG["model"]["image_size"], "resize": CONFIG["model"]["resize"], "mean": MEAN, "std": STD,
        "num_classes": len(labels), "confidence_threshold": CONFIG["evaluation"]["confidence_threshold"],
    }, indent=2), encoding="utf-8")
    (STAGING / "training_metadata.json").write_text(json.dumps({
        "model_version": version, "dataset_version": dataset_report["dataset_version"],
        "training_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "framework": {"torch": torch.__version__, "torchvision": __import__("torchvision").__version__},
        "device": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
        "train_images": len(train_items), "validation_images": len(val_items),
        "best_epoch": best["epoch"], "validation_accuracy": round(best["accuracy"], 4),
        "validation_macro_f1": round(best["macro_f1"], 4), "config": CONFIG, "history": history,
    }, indent=2), encoding="utf-8")
    print(f"best {best['epoch']}: val macro-F1 {best['macro_f1']:.3f} → {STAGING.relative_to(ROOT)} (version {version})")


if __name__ == "__main__":
    main()
