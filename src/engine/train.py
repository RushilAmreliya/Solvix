"""
NowCast Fusion — CNN Training Script

Trains a lightweight SimpleNowcastCNN on historical GPM precipitation data.
Model architecture is imported from src.engine.nowcast_model (single source of truth).

Usage:
    python -m src.engine.train
"""
import os

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

# ── Shared model definition (no more copy-paste) ──────────────────────────────
from src.engine.nowcast_model import SimpleNowcastCNN


# ─── Dataset ──────────────────────────────────────────────────────────────────
class WeatherDataset(Dataset):
    """
    Sliding-window dataset over a (T, H, W) precipitation data cube.

    Each sample is (X, Y) where:
        X: `seq_in`  consecutive frames as input  (past observations)
        Y: `seq_out` consecutive frames as target  (future to predict)
    """

    def __init__(self, data_path: str, seq_in: int = 3, seq_out: int = 3):
        """
        Args:
            data_path: Path to .npy file of shape (T, H, W) in mm/hr
            seq_in:    Number of past frames used as model input  (default 3 = 1.5 hrs)
            seq_out:   Number of future frames to predict          (default 3 = 1.5 hrs)
        """
        print(f"Loading dataset from {data_path} ...")
        self.data = np.load(data_path).astype(np.float32)

        # Normalise to [0, 1] — neural networks train much better on normalised data
        self.max_val = float(np.max(self.data))
        if self.max_val > 0:
            self.data /= self.max_val

        self.seq_in    = seq_in
        self.seq_out   = seq_out
        self.total_seq = seq_in + seq_out

        print(
            f"Dataset: shape={np.load(data_path).shape}, "
            f"max_precip={self.max_val:.2f} mm/hr, "
            f"samples={len(self)}"
        )

    def __len__(self) -> int:
        return max(0, len(self.data) - self.total_seq)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.data[idx             : idx + self.seq_in]
        y = self.data[idx + self.seq_in : idx + self.total_seq]
        return torch.from_numpy(x), torch.from_numpy(y)


# ─── Training Loop ────────────────────────────────────────────────────────────
def train_model() -> None:
    # ── Paths ──────────────────────────────────────────────────────────────────
    data_path  = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/assam_gpm_sample.npy")
    )
    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "nowcast_model.pth")
    )

    if not os.path.exists(data_path):
        print(
            f"Error: data file not found at {data_path}\n"
            "Run: python -m src.engine.fetch_gee_data"
        )
        return

    # ── Hyperparameters ────────────────────────────────────────────────────────
    SEQ_IN        = 3       # Look at past 1.5 hours
    SEQ_OUT       = 3       # Predict next 1.5 hours
    BATCH_SIZE    = 8
    EPOCHS        = 10
    LEARNING_RATE = 1e-3

    # ── Data ───────────────────────────────────────────────────────────────────
    dataset    = WeatherDataset(data_path, seq_in=SEQ_IN, seq_out=SEQ_OUT)
    train_size = int(0.8 * len(dataset))
    test_size  = len(dataset) - train_size
    train_ds, test_ds = torch.utils.data.random_split(dataset, [train_size, test_size])

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # ── Model ──────────────────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    model     = SimpleNowcastCNN(in_channels=SEQ_IN, out_channels=SEQ_OUT).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # ── Training ───────────────────────────────────────────────────────────────
    for epoch in range(1, EPOCHS + 1):
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

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                val_loss += criterion(model(batch_x), batch_y).item()
        avg_val = val_loss / len(test_loader)

        print(
            f"Epoch [{epoch:02d}/{EPOCHS}]  "
            f"Train Loss: {avg_train:.6f}  |  Val Loss: {avg_val:.6f}"
        )

    # ── Save ───────────────────────────────────────────────────────────────────
    torch.save(model.state_dict(), model_path)
    print(f"\n✅ Training complete! Model saved to {model_path}")


if __name__ == "__main__":
    train_model()
