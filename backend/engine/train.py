"""
NowCast Fusion — U-Net Training Script

Trains UNetNowcast on historical GPM/PERSIANN precipitation data.
Model architecture is imported from backend.engine.nowcast_model (single source of truth).

Usage:
    python -m backend.engine.train

Outputs:
    backend/engine/nowcast_model.pth  — trained model weights
"""
import os

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

# ── Shared model definition (single source of truth) ─────────────────────────
from backend.engine.nowcast_model import UNetNowcast


# ─── Dataset ──────────────────────────────────────────────────────────────────

class WeatherDataset(Dataset):
    """
    Sliding-window dataset over a (T, H, W) precipitation data cube.

    Each sample is (X, Y) where:
        X: `seq_in`  consecutive frames as input  (past observations)
        Y: `seq_out` consecutive frames as target  (future to predict)
    """

    def __init__(self, data_path: str, seq_in: int = 3, seq_out: int = 3) -> None:
        """
        Args:
            data_path: Path to .npy file of shape (T, H, W) in mm/hr
            seq_in:    Number of past frames used as model input  (default 3 = 1.5 hrs)
            seq_out:   Number of future frames to predict          (default 3 = 1.5 hrs)
        """
        print(f"Loading dataset from {data_path} ...")
        raw = np.load(data_path).astype(np.float32)

        # Normalise to [0, 1] — neural networks train much better on normalised data
        self.max_val = float(np.max(raw))
        self.data    = raw / self.max_val if self.max_val > 0 else raw

        self.seq_in    = seq_in
        self.seq_out   = seq_out
        self.total_seq = seq_in + seq_out

        print(
            f"Dataset: shape={raw.shape}, "
            f"max_precip={self.max_val:.2f} mm/hr, "
            f"samples={len(self)}"
        )

    def __len__(self) -> int:
        return max(0, len(self.data) - self.total_seq)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.data[idx              : idx + self.seq_in]
        y = self.data[idx + self.seq_in : idx + self.total_seq]
        return torch.from_numpy(x), torch.from_numpy(y)


# ─── Evaluation Metrics ───────────────────────────────────────────────────────

def compute_csi(pred: np.ndarray, target: np.ndarray, threshold: float = 0.1) -> float:
    """
    Critical Success Index (CSI / Threat Score).
    Standard metric for precipitation forecasting skill.
    CSI = TP / (TP + FP + FN)   range [0, 1], higher is better.

    Args:
        pred:      Predicted precipitation array (normalised [0,1])
        target:    Ground-truth array (normalised [0,1])
        threshold: Detection threshold (default 0.1 = 10% of max)
    Returns:
        CSI score as float
    """
    p = pred   >= threshold
    t = target >= threshold
    tp = int(np.sum( p &  t))
    fp = int(np.sum( p & ~t))
    fn = int(np.sum(~p &  t))
    denom = tp + fp + fn
    return tp / denom if denom > 0 else 1.0


def compute_ets(pred: np.ndarray, target: np.ndarray, threshold: float = 0.1) -> float:
    """
    Equitable Threat Score (ETS / Gilbert Skill Score).
    Corrects CSI for random chance hits.
    ETS ∈ (-1/3, 1], 0 = no skill, 1 = perfect, > 0 = skilful.

    Args:
        pred:      Predicted precipitation array (normalised [0,1])
        target:    Ground-truth array (normalised [0,1])
        threshold: Detection threshold
    Returns:
        ETS score as float
    """
    p = pred   >= threshold
    t = target >= threshold
    tp = int(np.sum( p &  t))
    fp = int(np.sum( p & ~t))
    fn = int(np.sum(~p &  t))
    tn = int(np.sum(~p & ~t))
    n  = tp + fp + fn + tn

    # Expected hits by chance
    hits_random = (tp + fp) * (tp + fn) / n if n > 0 else 0
    denom = tp + fp + fn - hits_random
    return (tp - hits_random) / denom if denom != 0 else 0.0


# ─── Training Loop ────────────────────────────────────────────────────────────

def train_model() -> None:
    # ── Paths (Prioritize 4km PERSIANN dataset over 10km GPM) ─────────────────
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

    dataset_label = "4km PERSIANN-CCS" if "4km" in data_path else "10km GPM"
    print(f"[*] Training on {dataset_label} dataset: {data_path}")

    # ── Hyperparameters ────────────────────────────────────────────────────────
    SEQ_IN        = 3       # Look at past 1.5 hours
    SEQ_OUT       = 3       # Predict next 1.5 hours
    BATCH_SIZE    = 4       # Smaller batch to fit U-Net on CPU
    EPOCHS        = 15
    LEARNING_RATE = 1e-3

    # ── Data ───────────────────────────────────────────────────────────────────
    dataset = WeatherDataset(data_path, seq_in=SEQ_IN, seq_out=SEQ_OUT)

    # ── Chronological Train/Val Split (No Sliding-Window Leakage) ──────────────
    # Time-series nowcasting requires strict temporal splitting instead of random
    # sampling. We enforce a buffer gap of total_seq frames so no test sample
    # shares any observation frames with the training set.
    train_ratio = 0.8
    train_size = int(train_ratio * len(dataset))
    buffer_gap = dataset.total_seq
    test_start_idx = min(train_size + buffer_gap, len(dataset))

    train_ds = torch.utils.data.Subset(dataset, list(range(0, train_size)))
    test_ds  = torch.utils.data.Subset(dataset, list(range(test_start_idx, len(dataset))))

    print(
        f"[*] Chronological Split: {len(train_ds)} train samples [0..{train_size-1}], "
        f"{len(test_ds)} validation samples [{test_start_idx}..{len(dataset)-1}]"
    )
    print(
        f"[*] Temporal isolation buffer: {buffer_gap} frames ({buffer_gap * 0.5:.1f} hrs) "
        f"between train and test splits to prevent sliding-window data leakage."
    )

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # ── Model ──────────────────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training on device: {device}")
    print("[*] Model: UNetNowcast (encoder-decoder with skip connections)")

    model     = UNetNowcast(in_channels=SEQ_IN, out_channels=SEQ_OUT).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[*] Trainable parameters: {n_params:,}")

    # ── Training ───────────────────────────────────────────────────────────────
    best_val_loss = float("inf")

    for epoch in range(1, EPOCHS + 1):
        # — Train —
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            predictions = model(batch_x)
            loss        = criterion(predictions, batch_y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        avg_train = train_loss / len(train_loader)

        # — Validate + compute CSI/ETS —
        model.eval()
        val_loss   = 0.0
        all_preds  = []
        all_targets = []
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                pred    = model(batch_x)
                val_loss += criterion(pred, batch_y).item()
                all_preds.append(pred.cpu().numpy())
                all_targets.append(batch_y.cpu().numpy())

        avg_val = val_loss / len(test_loader)
        scheduler.step(avg_val)

        # Compute skill scores on validation set
        preds_np   = np.concatenate(all_preds,   axis=0)
        targets_np = np.concatenate(all_targets, axis=0)
        csi = compute_csi(preds_np, targets_np, threshold=0.1)
        ets = compute_ets(preds_np, targets_np, threshold=0.1)

        print(
            f"Epoch [{epoch:02d}/{EPOCHS}]  "
            f"Train Loss: {avg_train:.6f}  |  "
            f"Val Loss: {avg_val:.6f}  |  "
            f"CSI: {csi:.3f}  |  ETS: {ets:.3f}"
        )

        # Save best checkpoint
        if avg_val < best_val_loss:
            best_val_loss = avg_val
            torch.save(model.state_dict(), model_path)
            print(f"  [OK] Best model saved (val_loss={avg_val:.6f})")

    print(f"\n[OK] Training complete! Best model saved to {model_path}")
    print(f"     Final metrics -- CSI: {csi:.3f}  ETS: {ets:.3f}")
    print("     Restart the backend to load the new U-Net weights.")


if __name__ == "__main__":
    train_model()
