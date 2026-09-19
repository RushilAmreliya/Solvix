"""
NowCast Fusion -- U-Net Training Script (v2, accuracy-focused)

Key improvements over v1:
  1. RainWeightedLoss    -- upweights rain pixels 20x so "predict zero" is no longer optimal
  2. stratified_split    -- val set picks the RAINIEST frames from across the dataset,
                            not just the dry chronological tail (monsoon tail = dry season)
  3. Lower CSI threshold -- 0.01 normalised (~0.58 mm/hr) vs old 0.10 (~5.83 mm/hr)
  4. Multi-threshold CSI -- reports at light / moderate / heavy rain thresholds
  5. 30 epochs + cosine LR annealing + gradient clipping

Usage:
    python -m backend.engine.train

Outputs:
    backend/engine/nowcast_model.pth  -- best checkpoint (lowest val loss OR best CSI)
"""
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset

from backend.engine.nowcast_model import UNetNowcast


# ---- Rain-Weighted Loss ------------------------------------------------------

class RainWeightedLoss(nn.Module):
    """
    Weighted MSE + small L1 term for precipitation nowcasting on sparse fields.

    Standard MSE on a field that is 67% zero gives minimum loss by predicting
    zero everywhere. This loss upweights rain pixels so the model is forced to
    learn where and how much it rains.

        L = mean( w(y) * (pred - y)^2 ) + alpha * L1_on_rain_pixels

    where  w(y) = 1 + (rain_weight - 1) * I[y > rain_threshold]
    """

    def __init__(
        self,
        rain_weight: float = 20.0,
        rain_threshold: float = 0.01,   # ~0.58 mm/hr in normalised space
        l1_alpha: float = 0.05,
    ) -> None:
        super().__init__()
        self.rain_weight    = rain_weight
        self.rain_threshold = rain_threshold
        self.l1_alpha       = l1_alpha

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        mse_px    = F.mse_loss(pred, target, reduction='none')
        rain_mask = (target > self.rain_threshold).float()
        weight    = 1.0 + (self.rain_weight - 1.0) * rain_mask
        wmse      = (mse_px * weight).mean()
        l1_rain   = (F.l1_loss(pred, target, reduction='none') * rain_mask).sum() \
                    / (rain_mask.sum() + 1e-6)
        return wmse + self.l1_alpha * l1_rain


# ---- Dataset -----------------------------------------------------------------

class WeatherDataset(Dataset):
    """Sliding-window dataset over a (T, H, W) precipitation cube."""

    def __init__(self, data_path: str, seq_in: int = 3, seq_out: int = 3) -> None:
        print(f"Loading dataset from {data_path} ...")
        raw = np.load(data_path).astype(np.float32)

        self.max_val   = float(np.max(raw))
        self.data      = raw / self.max_val if self.max_val > 0 else raw
        self.seq_in    = seq_in
        self.seq_out   = seq_out
        self.total_seq = seq_in + seq_out

        print(
            f"Dataset: shape={raw.shape}, max={self.max_val:.2f} mm/hr, "
            f"mean={raw.mean():.4f} mm/hr, samples={len(self)}"
        )

    def __len__(self) -> int:
        return max(0, len(self.data) - self.total_seq)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.data[idx              : idx + self.seq_in]
        y = self.data[idx + self.seq_in : idx + self.total_seq]
        return torch.from_numpy(x), torch.from_numpy(y)

    def sample_rain_intensity(self) -> np.ndarray:
        """Mean target rainfall intensity for every sample (used for stratified split)."""
        out = np.zeros(len(self), dtype=np.float32)
        for i in range(len(self)):
            out[i] = float(self.data[i + self.seq_in : i + self.total_seq].mean())
        return out


# ---- Stratified Split --------------------------------------------------------

def stratified_split(
    dataset: WeatherDataset,
    val_fraction: float = 0.20,
    min_gap: int = 6,
) -> tuple[list[int], list[int]]:
    """
    Build train/val index lists ensuring val contains RAINY frames, not just
    the dry chronological tail.

    Algorithm (greedy rain-ranked selection):
      1. Rank all sample indices by target rainfall intensity (highest first).
      2. Greedily select val candidates from this ranking, enforcing that any
         two consecutive val picks are at least min_gap frames apart in time.
         This prevents val frames from clustering and ensures spread.
      3. Everything not in val goes to train.

    Why not enforce gap vs all training frames?
      Enforcing |val_i - train_j| > gap for ALL j eliminates every candidate
      because every index has nearby neighbours in the 282-sample dataset.
      The only constraint needed is that val picks don't cluster together.
    """
    n            = len(dataset)
    intensities  = dataset.sample_rain_intensity()
    target_val_n = max(int(val_fraction * n), 10)

    # Sort by rainfall descending -- pick val from rainiest frames first
    sorted_by_rain = np.argsort(intensities)[::-1]

    selected_val = []
    selected_set = set()

    for idx in map(int, sorted_by_rain):
        if len(selected_val) >= target_val_n:
            break
        # Only enforce gap between already-chosen val frames (not vs all train)
        too_close = any(abs(idx - v) < min_gap for v in selected_val)
        if not too_close:
            selected_val.append(idx)
            selected_set.add(idx)

    # Safety: fill from chronological tail if still short
    if len(selected_val) < target_val_n:
        for idx in range(n - 1, -1, -1):
            if idx not in selected_set:
                too_close = any(abs(idx - v) < min_gap for v in selected_val)
                if not too_close:
                    selected_val.append(idx)
                    selected_set.add(idx)
            if len(selected_val) >= target_val_n:
                break

    val_indices   = sorted(selected_val)
    train_indices = [i for i in range(n) if i not in selected_set]
    return train_indices, val_indices


# ---- Metrics -----------------------------------------------------------------

def compute_csi(pred: np.ndarray, target: np.ndarray, threshold: float) -> float:
    p, t   = pred >= threshold, target >= threshold
    tp, fp, fn = np.sum(p & t), np.sum(p & ~t), np.sum(~p & t)
    d = int(tp + fp + fn)
    return float(tp) / d if d > 0 else 1.0


def compute_ets(pred: np.ndarray, target: np.ndarray, threshold: float) -> float:
    p, t   = pred >= threshold, target >= threshold
    tp, fp, fn, tn = (int(np.sum(p & t)), int(np.sum(p & ~t)),
                      int(np.sum(~p & t)), int(np.sum(~p & ~t)))
    n = tp + fp + fn + tn
    if n == 0:
        return 0.0
    rand_hits = (tp + fp) * (tp + fn) / n
    denom     = tp + fp + fn - rand_hits
    return float((tp - rand_hits) / denom) if denom != 0 else 0.0


def report_metrics(
    preds: np.ndarray,
    targets: np.ndarray,
    max_val: float,
    label: str = "",
) -> float:
    """Report CSI/ETS at light/moderate/heavy thresholds. Returns light-rain CSI."""
    thresholds = [
        (0.01, f">={0.01 * max_val:.1f} mm/hr (light)"),
        (0.05, f">={0.05 * max_val:.1f} mm/hr (moderate)"),
        (0.10, f">={0.10 * max_val:.1f} mm/hr (heavy)"),
    ]
    first_csi = 0.0
    for i, (thr, lbl) in enumerate(thresholds):
        csi = compute_csi(preds, targets, thr)
        ets = compute_ets(preds, targets, thr)
        print(f"    {label}[{lbl}]  CSI={csi:.3f}  ETS={ets:.3f}")
        if i == 0:
            first_csi = csi
    return first_csi


# ---- Training Loop -----------------------------------------------------------

def train_model() -> None:
    data_4km  = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/assam_persiann_4km.npy")
    )
    data_10km = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/assam_gpm_sample.npy")
    )
    data_path  = data_4km if os.path.exists(data_4km) else data_10km
    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "nowcast_model.pth")
    )

    if not os.path.exists(data_path):
        print(f"Error: data file not found at {data_path}")
        return

    label = "4km PERSIANN-CCS" if "4km" in data_path else "10km GPM"
    print(f"[*] Training on {label}: {data_path}")

    SEQ_IN        = 3
    SEQ_OUT       = 3
    BATCH_SIZE    = 4
    EPOCHS        = 30
    LEARNING_RATE = 5e-4
    GRAD_CLIP     = 1.0

    dataset = WeatherDataset(data_path, seq_in=SEQ_IN, seq_out=SEQ_OUT)

    print("[*] Computing stratified train/val split ...")
    train_idx, val_idx = stratified_split(dataset, val_fraction=0.20, min_gap=6)

    intensities     = dataset.sample_rain_intensity()
    val_rainy_count = int((intensities[val_idx] > 0.01).sum())
    print(
        f"[*] Split: {len(train_idx)} train | {len(val_idx)} val\n"
        f"    Train mean intensity: {intensities[train_idx].mean() * dataset.max_val:.4f} mm/hr\n"
        f"    Val   mean intensity: {intensities[val_idx].mean()   * dataset.max_val:.4f} mm/hr\n"
        f"    Val rainy samples (>0.01 norm = >{0.01*dataset.max_val:.2f} mm/hr): "
        f"{val_rainy_count}/{len(val_idx)}"
    )

    train_loader = DataLoader(Subset(dataset, train_idx), batch_size=BATCH_SIZE,
                              shuffle=True, num_workers=0)
    val_loader   = DataLoader(Subset(dataset, val_idx),   batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=0)

    device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model     = UNetNowcast(in_channels=SEQ_IN, out_channels=SEQ_OUT).to(device)
    criterion = RainWeightedLoss(rain_weight=20.0, rain_threshold=0.01, l1_alpha=0.05)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[*] Device: {device}  |  Params: {n_params:,}")
    print(f"[*] Loss: RainWeightedLoss(20x)  |  Epochs: {EPOCHS}  |  LR: {LEARNING_RATE}")
    print("-" * 72)

    best_val_loss = float("inf")
    best_csi      = 0.0
    preds_np = targets_np = None

    for epoch in range(1, EPOCHS + 1):
        # -- Train --
        model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            pred   = model(bx)
            loss   = criterion(pred, by)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            train_loss += loss.item()
        avg_train = train_loss / len(train_loader)

        # -- Validate --
        model.eval()
        val_loss, all_preds, all_targets = 0.0, [], []
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                pred   = model(bx)
                val_loss += criterion(pred, by).item()
                all_preds.append(pred.cpu().numpy())
                all_targets.append(by.cpu().numpy())

        avg_val    = val_loss / len(val_loader)
        preds_np   = np.concatenate(all_preds)
        targets_np = np.concatenate(all_targets)
        scheduler.step()

        csi = compute_csi(preds_np, targets_np, threshold=0.01)
        ets = compute_ets(preds_np, targets_np, threshold=0.01)
        lr  = optimizer.param_groups[0]['lr']

        print(
            f"Epoch [{epoch:02d}/{EPOCHS}]  "
            f"Train: {avg_train:.5f}  Val: {avg_val:.5f}  "
            f"CSI: {csi:.3f}  ETS: {ets:.3f}  LR: {lr:.2e}"
        )

        improved = avg_val < best_val_loss or csi > best_csi
        if avg_val < best_val_loss:
            best_val_loss = avg_val
        if csi > best_csi:
            best_csi = csi
        if improved:
            torch.save(model.state_dict(), model_path)
            print(f"  [OK] Saved (val={avg_val:.5f}, CSI={csi:.3f})")

    # -- Final report --
    print("\n" + "=" * 72)
    print("[OK] Training complete. Final val metrics (all thresholds):")
    report_metrics(preds_np, targets_np, dataset.max_val)

    rain_mask = targets_np.mean(axis=(1, 2, 3)) > 0.001
    if rain_mask.sum() > 0:
        print(f"\n  Rainy samples only ({rain_mask.sum()}/{len(rain_mask)}):")
        report_metrics(preds_np[rain_mask], targets_np[rain_mask],
                       dataset.max_val, label="RAINY ")

    print(f"\n  Best CSI (light rain >{0.01*dataset.max_val:.2f} mm/hr): {best_csi:.3f}")
    print(f"  Model saved: {model_path}")
    print("  Restart the backend to load the new weights.")


if __name__ == "__main__":
    train_model()
