"""
NowCast Fusion — Shared CNN Model Definition
Imported by both src/engine/train.py and src/backend/main.py.
Keeps the model architecture in a single place.
"""
import torch.nn as nn


class SimpleNowcastCNN(nn.Module):
    """
    Lightweight Convolutional Neural Network for spatiotemporal precipitation prediction.

    Treats the sequence of T past frames as T input channels, allowing standard
    Conv2D layers to learn both spatial and short-range temporal patterns.
    Fast enough to train on a laptop CPU in minutes — ideal for a hackathon.

    Args:
        in_channels:  Number of past frames used as input  (default: 3 = 1.5 hours)
        out_channels: Number of future frames to predict   (default: 3 = 1.5 hours)
    """

    def __init__(self, in_channels: int = 3, out_channels: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, out_channels, kernel_size=3, padding=1),
            nn.ReLU(),  # Ensures non-negative precipitation output
        )

    def forward(self, x):
        return self.net(x)
