"""
NowCast Fusion — U-Net Nowcasting Model

Replaces the original SimpleNowcastCNN with a proper U-Net architecture.
U-Net is the standard choice for spatiotemporal precipitation prediction:
  - Encoder (downsampling) path captures large-scale storm structure
  - Decoder (upsampling) path reconstructs fine-grained spatial detail
  - Skip connections preserve high-resolution features across scales
  - Uses dynamic interpolation to guarantee exact spatial alignment with skip
    connections regardless of input grid dimensions (e.g. 100x155, 40x62)

This is imported by both backend/engine/train.py and backend/main.py.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


# ─── Building Block ───────────────────────────────────────────────────────────

class _DoubleConv(nn.Module):
    """Two successive Conv2d → BatchNorm → ReLU blocks (the U-Net 'cell')."""

    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


# ─── U-Net ────────────────────────────────────────────────────────────────────

class UNetNowcast(nn.Module):
    """
    U-Net for precipitation nowcasting.

    Treats the sequence of T past precipitation frames as T input channels
    (one channel per timestep), allowing the network to learn both spatial
    patterns and short-range temporal evolution simultaneously.

    Architecture:
        Encoder:    3 downsampling stages (max-pool + double-conv)
        Bottleneck: double-conv at lowest spatial resolution
        Decoder:    3 upsampling stages (size-matched bilinear + skip-concat + double-conv)
        Head:       1×1 conv → ReLU to ensure non-negative precipitation

    Args:
        in_channels:  Number of past frames fed as input  (default: 3 = 1.5 hrs)
        out_channels: Number of future frames to predict  (default: 3 = 1.5 hrs)
        features:     Base feature count (doubles at each encoder stage)
    """

    def __init__(
        self,
        in_channels:  int = 3,
        out_channels: int = 3,
        features:     int = 32,
    ) -> None:
        super().__init__()

        # ── Encoder ──────────────────────────────────────────────────────────
        self.enc1 = _DoubleConv(in_channels, features)          # → (B, 32,  H,   W)
        self.enc2 = _DoubleConv(features,    features * 2)      # → (B, 64,  H/2, W/2)
        self.enc3 = _DoubleConv(features * 2, features * 4)     # → (B, 128, H/4, W/4)

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # ── Bottleneck ────────────────────────────────────────────────────────
        self.bottleneck = _DoubleConv(features * 4, features * 8)  # → (B, 256, H/8, W/8)

        # ── Decoder ──────────────────────────────────────────────────────────
        self.dec3 = _DoubleConv(features * 8 + features * 4, features * 4)
        self.dec2 = _DoubleConv(features * 4 + features * 2, features * 2)
        self.dec1 = _DoubleConv(features * 2 + features,     features)

        # ── Output Head ───────────────────────────────────────────────────────
        self.head = nn.Sequential(
            nn.Conv2d(features, out_channels, kernel_size=1),
            nn.ReLU(inplace=True),   # Precipitation must be ≥ 0
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, in_channels, H, W) — batch of precipitation sequences
        Returns:
            (B, out_channels, H, W) — predicted future precipitation frames
        """
        # Encoder — save skip features
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))

        # Bottleneck
        b = self.bottleneck(self.pool(e3))

        # Decoder — dynamically match spatial resolution with skip connections
        u3 = F.interpolate(b, size=e3.shape[2:], mode="bilinear", align_corners=True)
        d3 = self.dec3(torch.cat([u3, e3], dim=1))

        u2 = F.interpolate(d3, size=e2.shape[2:], mode="bilinear", align_corners=True)
        d2 = self.dec2(torch.cat([u2, e2], dim=1))

        u1 = F.interpolate(d2, size=e1.shape[2:], mode="bilinear", align_corners=True)
        d1 = self.dec1(torch.cat([u1, e1], dim=1))

        return self.head(d1)


# ─── Backwards-compatibility alias ───────────────────────────────────────────
SimpleNowcastCNN = UNetNowcast
