# train_resnet18_on_masks.py
import argparse
import os
from pathlib import Path
import random
from typing import List, Tuple, Dict

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms import InterpolationMode
import torchvision.transforms as T
import timm
from tqdm.auto import tqdm  # ★ tqdm


# ---------------------------
# Utils
# ---------------------------
def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def stratified_split(paths_by_class: Dict[int, List[Path]], train_ratio: float, seed: int) -> Tuple[List[Tuple[Path,int]], List[Tuple[Path,int]]]:
    rng = random.Random(seed)
    train, val = [], []
    for y, paths in paths_by_class.items():
        paths = list(paths)
        rng.shuffle(paths)
        n = len(paths)
        k = int(round(n * train_ratio))
        train += [(p, y) for p in paths[:k]]
        val   += [(p, y) for p in paths[k:]]
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def save_split_list(pairs: List[Tuple[Path,int]], out_txt: Path):
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    with open(out_txt, "w", encoding="utf-8") as f:
        for p, y in pairs:
            f.write(f"{p.as_posix()}\t{y}\n")


def load_split_list(txt: Path) -> List[Tuple[Path,int]]:
    pairs = []
    with open(txt, "r", encoding="utf-8") as f:
        for line in f:
            path_str, y_str = line.strip().split("\t")
            pairs.append((Path(path_str), int(y_str)))
    return pairs


# ---------------------------
# Mask → [V,L,O] one-hot (3ch)
# ---------------------------
def _to_numpy_rgb(img: Image.Image) -> np.ndarray:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img)  # (H, W, 3) uint8


def _to_numpy_l(img: Image.Image) -> np.ndarray:
    if img.mode != "L":
        img = img.convert("L")
    return np.asarray(img)  # (H, W) uint8


def _match_color(arr: np.ndarray, rgb: Tuple[int,int,int], tol: int = 10) -> np.ndarray:
    r, g, b = rgb
    diff = np.abs(arr.astype(np.int16) - np.array([r, g, b], dtype=np.int16))
    return (diff <= tol).all(axis=-1)


def mask_to_VLO(mask_img: Image.Image, mask_mode: str = "auto") -> np.ndarray:
    """
    Returns one-hot [V, L, O] float32 in [0,1], shape (3, H, W).
    Supports:
      - id map (0:bg, 1:vehicle, 2:lane, 3:overlap)
      - color map (RGB): vehicle≈green, lane≈red, overlap≈cyan
    """
    if mask_mode == "auto":
        if mask_img.mode == "L":
            mask_arr = _to_numpy_l(mask_img)
            uniq = np.unique(mask_arr)
            if np.all(np.isin(uniq, [0,1,2,3])):
                mask_mode = "id"
            else:
                mask_mode = "id"
        else:
            mask_mode = "color"

    if mask_mode == "id":
        m = _to_numpy_l(mask_img)  # (H,W)
        V = (m == 1)
        L = (m == 2)
        O = (m == 3)
    else:
        arr = _to_numpy_rgb(mask_img)  # (H,W,3)
        V = _match_color(arr, (0, 255, 0))
        L = _match_color(arr, (255, 0, 0))
        O = _match_color(arr, (0, 255, 255))

    vlo = np.stack([V.astype(np.float32), L.astype(np.float32), O.astype(np.float32)], axis=0)  # (3,H,W)
    return vlo


# ---------------------------
# Dataset
# ---------------------------
CLASS_NAME_TO_ID = {"normal": 0, "danger": 1, "violation": 2}

class MaskVLODataset(Dataset):
    def __init__(self, pairs: List[Tuple[Path,int]], img_size: int = 224, is_train: bool = True,
                 mask_mode: str = "auto"):
        self.pairs = pairs
        self.is_train = is_train
        self.mask_mode = mask_mode

        if is_train:
            self.tf = T.Compose([
                T.RandomResizedCrop(size=img_size, scale=(0.7, 1.0), interpolation=InterpolationMode.NEAREST),
                T.RandomHorizontalFlip(p=0.5),
            ])
        else:
            self.tf = T.Compose([
                T.Resize(256, interpolation=InterpolationMode.NEAREST),
                T.CenterCrop(img_size),
            ])

        self.to_tensor = T.Compose([T.ToTensor()])  # -> float [0,1], CHW

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx: int):
        path, y = self.pairs[idx]
        mask_img = Image.open(path)
        vlo = mask_to_VLO(mask_img, self.mask_mode)  # (3,H,W) float32 [0,1]

        # transforms expect PIL -> fake-RGB with VLO channels as R,G,B
        vlo_uint8 = (vlo * 255.0).astype(np.uint8)
        pil = Image.merge("RGB", [Image.fromarray(vlo_uint8[c]) for c in range(3)])
        pil = self.tf(pil)

        vlo_tensor = self.to_tensor(pil)  # (3,H,W), float32 [0,1]
        label = torch.tensor(y, dtype=torch.long)
        return vlo_tensor, label


# ---------------------------
# Metrics
# ---------------------------
@torch.no_grad()
def evaluate(model: torch.nn.Module, loader: DataLoader, device: torch.device, num_classes: int = 3,
             show_progress: bool = True):
    model.eval()
    total = 0
    correct = 0
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)

    iterator = tqdm(loader, desc="[val] batches", dynamic_ncols=True, leave=False) if show_progress else loader
    for x, y in iterator:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        logits = model(x)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.size(0)

        for t, p in zip(y.cpu().numpy(), pred.cpu().numpy()):
            cm[t, p] += 1

        if show_progress:
            acc_so_far = correct / max(1, total)
            iterator.set_postfix(acc=f"{acc_so_far:.3f}")

    acc = correct / max(1, total)

    per_f1 = []
    for i in range(num_classes):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        prec = tp / max(1, (tp + fp))
        rec  = tp / max(1, (tp + fn))
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_f1.append(f1)
    macro_f1 = float(np.mean(per_f1))

    return acc, macro_f1, per_f1, cm


def compute_class_weights(pairs: List[Tuple[Path,int]], num_classes: int = 3) -> torch.Tensor:
    counts = np.zeros(num_classes, dtype=np.int64)
    for _, y in pairs:
        counts[y] += 1
    counts = np.clip(counts, 1, None)
    inv = 1.0 / counts
    w = inv * (num_classes / inv.sum())
    return torch.tensor(w, dtype=torch.float32)


# ---------------------------
# Scan dataset
# ---------------------------
def scan_mask_dataset(root: Path) -> Dict[int, List[Path]]:
    mask_dir = root / "mask"
    if not mask_dir.exists():
        raise FileNotFoundError(f"'mask' folder not found under: {root}")

    paths_by_class: Dict[int, List[Path]] = {0: [], 1: [], 2: []}
    for name, y in CLASS_NAME_TO_ID.items():
        sub = mask_dir / name
        if not sub.exists():
            raise FileNotFoundError(f"Missing folder: {sub}")
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
            paths_by_class[y] += list(sub.rglob(ext))
    return paths_by_class


# ---------------------------
# Train
# ---------------------------
def train(args):
    set_seed(args.seed)

    root = Path(args.data_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # prepare split
    split_dir = out_dir / "splits"
    train_txt = split_dir / "train.txt"
    val_txt   = split_dir / "val.txt"

    if train_txt.exists() and val_txt.exists() and not args.rebuild_split:
        train_pairs = load_split_list(train_txt)
        val_pairs   = load_split_list(val_txt)
        print(f"[Split] Loaded existing split: {len(train_pairs)} train / {len(val_pairs)} val")
    else:
        paths_by_class = scan_mask_dataset(root)
        train_pairs, val_pairs = stratified_split(paths_by_class, args.train_ratio, args.seed)
        save_split_list(train_pairs, train_txt)
        save_split_list(val_pairs, val_txt)
        print(f"[Split] Built new split: {len(train_pairs)} train / {len(val_pairs)} val  (saved under {split_dir})")

    device = torch.device("cuda" if torch.cuda.is_available() and args.device != "cpu" else "cpu")
    print(f"[Device] {device}")

    train_ds = MaskVLODataset(train_pairs, img_size=args.img_size, is_train=True,  mask_mode=args.mask_mode)
    val_ds   = MaskVLODataset(val_pairs,   img_size=args.img_size, is_train=False, mask_mode=args.mask_mode)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=args.num_workers, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                              num_workers=args.num_workers, pin_memory=True)

    # Model
    model = timm.create_model("resnet18", pretrained=True, num_classes=3, in_chans=3)
    model.to(device)

    # Loss (class weights for imbalance)
    class_weights = compute_class_weights(train_pairs).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda" and args.amp))

    best_f1 = -1.0
    (out_dir / "checkpoints").mkdir(exist_ok=True, parents=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0
        correct = 0
        running_loss = 0.0

        pbar = tqdm(train_loader, desc=f"[train] epoch {epoch}/{args.epochs}", dynamic_ncols=True)
        for x, y in pbar:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda" and args.amp)):
                logits = model(x)
                loss = criterion(logits, y)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * y.size(0)
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total   += y.size(0)

            train_loss = running_loss / max(1, total)
            train_acc  = correct / max(1, total)
            pbar.set_postfix(loss=f"{train_loss:.4f}", acc=f"{train_acc:.4f}",
                             lr=f"{optimizer.param_groups[0]['lr']:.2e}")

        # Eval with tqdm bar
        val_acc, val_macro_f1, per_f1, cm = evaluate(model, val_loader, device, num_classes=3,
                                                     show_progress=not args.no_tqdm)
        scheduler.step()

        print(f"[{epoch:03d}/{args.epochs}] "
              f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
              f"val_acc={val_acc:.4f} val_macroF1={val_macro_f1:.4f} "
              f"per_class_f1={[f'{x:.3f}' for x in per_f1]}")

        # Save
        is_best = val_macro_f1 > best_f1
        if is_best:
            best_f1 = val_macro_f1
            torch.save({
                "epoch": epoch,
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "class_weights": class_weights,
                "args": vars(args),
            }, out_dir / "checkpoints" / "best.pth")

        torch.save({
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "class_weights": class_weights,
            "args": vars(args),
        }, out_dir / "checkpoints" / "last.pth")

    print(f"[Done] Best val macro-F1 = {best_f1:.4f}  (ckpt: {out_dir/'checkpoints'/'best.pth'})")


# ---------------------------
# CLI
# ---------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Fine-tune ResNet18 on [V,L,O] one-hot masks (Normal/Danger/Violation)")
    p.add_argument("--data_root", type=str,
                   default=r"C:\Users\chobh\Desktop\bigProject\Data\lane_violation_seg_cls_dataset_sampled",
                   help="Dataset root that contains 'mask/normal|danger|violation'")
    p.add_argument("--out_dir", type=str, default=r"C:\Users\chobh\Desktop\bigProject\Illegal-Parking-Detection\AI\Experiments\resnet18_mask_vlo")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch_size", type=int, default=256)
    p.add_argument("--img_size", type=int, default=224)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--train_ratio", type=float, default=0.8, help="Stratified train ratio")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num_workers", type=int, default=0, help="Windows 권장=0")
    p.add_argument("--device", type=str, default="cuda", choices=["cuda", "cpu"])
    p.add_argument("--mask_mode", type=str, default="auto", choices=["auto", "id", "color"],
                   help="mask가 id맵(0,1,2,3)인지 컬러 팔레트인지 지정. auto면 자동 판별")
    p.add_argument("--rebuild_split", action="store_true", help="기존 split 무시하고 새로 생성")
    p.add_argument("--amp", action="store_true", help="Enable mixed precision on CUDA")
    p.add_argument("--no_tqdm", action="store_true", help="Disable tqdm progress bars")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(args)
