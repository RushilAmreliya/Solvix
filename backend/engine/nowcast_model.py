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


# ─── ConvLSTM Cell ────────────────────────────────────────────────────────────

class ConvLSTMCell(nn.Module):
    """
    Single Convolutional LSTM cell.

    Combines spatial convolutions with gated recurrent state, allowing the
    network to model both *where* precipitation is spatially and *how* it
    is evolving temporally — superior to U-Net for lead times > +90 min.

    Args:
        in_channels:  Channels of the input feature map at this step.
        hidden_channels: Channels of the hidden / cell state tensors.
        kernel_size:  Conv kernel for all gates (default 3).
    """

    def __init__(self, in_channels: int, hidden_channels: int, kernel_size: int = 3) -> None:
        super().__init__()
        self.hidden_channels = hidden_channels
        pad = kernel_size // 2
        # Single conv to compute all 4 gates simultaneously (efficiency)
        self.conv = nn.Conv2d(
            in_channels + hidden_channels,
            4 * hidden_channels,
            kernel_size=kernel_size,
            padding=pad,
            bias=True,
        )

    def forward(
        self,
        x: torch.Tensor,
        h: torch.Tensor,
        c: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (B, in_channels, H, W) — input at current timestep
            h: (B, hidden_channels, H, W) — previous hidden state
            c: (B, hidden_channels, H, W) — previous cell state
        Returns:
            (h_new, c_new) of same spatial dimensions
        """
        combined = torch.cat([x, h], dim=1)
        gates = self.conv(combined)
        g_i, g_f, g_o, g_g = gates.chunk(4, dim=1)
        i = torch.sigmoid(g_i)
        f = torch.sigmoid(g_f)
        o = torch.sigmoid(g_o)
        g = torch.tanh(g_g)
        c_new = f * c + i * g
        h_new = o * torch.tanh(c_new)
        return h_new, c_new

    def init_hidden(
        self, batch_size: int, height: int, width: int, device: torch.device
    ) -> tuple[torch.Tensor, torch.Tensor]:
        h = torch.zeros(batch_size, self.hidden_channels, height, width, device=device)
        c = torch.zeros(batch_size, self.hidden_channels, height, width, device=device)
        return h, c


# ─── ConvLSTM Nowcasting Network ─────────────────────────────────────────────

class ConvLSTMNowcast(nn.Module):
    """
    Multi-layer Convolutional LSTM for precipitation nowcasting.

    Architecture:
        Encoder:  2× ConvLSTMCell layers processing the input sequence step-by-step,
                  building a rich spatiotemporal state representation.
        Decoder:  Iterative prediction of future frames using the encoder's
                  final hidden state as initial conditions. Each decoded frame
                  is fed back as input for the next step (autoregressive).
        Head:     1×1 conv → ReLU to enforce non-negative precipitation.

    Advantages over U-Net:
        - Explicitly models temporal dynamics across lead times.
        - Autoregressive decoding naturally extends to +3 hr / +6 hr forecasts
          while preserving cell structure memory.
        - Competitive with optical flow methods on convective initiation events.

    Args:
        in_channels:     Number of input frames (past timesteps).
        out_channels:    Number of output frames (future timesteps to predict).
        hidden_channels: Feature depth of ConvLSTM hidden states (default: 32).
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        hidden_channels: int = 32,
    ) -> None:
        super().__init__()
        self.out_channels = out_channels

        # Input projection: compress single-frame channels into feature space
        self.input_proj = nn.Conv2d(1, hidden_channels, kernel_size=3, padding=1, bias=False)

        # Encoder: 2 stacked ConvLSTM layers
        self.enc_cell1 = ConvLSTMCell(hidden_channels, hidden_channels)
        self.enc_cell2 = ConvLSTMCell(hidden_channels, hidden_channels)

        # Decoder: 2 stacked ConvLSTM layers (share architecture, own parameters)
        self.dec_cell1 = ConvLSTMCell(hidden_channels, hidden_channels)
        self.dec_cell2 = ConvLSTMCell(hidden_channels, hidden_channels)

        # Output head: map hidden state back to single-channel precipitation
        self.head = nn.Sequential(
            nn.Conv2d(hidden_channels, 1, kernel_size=1),
            nn.ReLU(inplace=True),  # Precipitation ≥ 0
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, in_channels, H, W) — batch of T past precipitation frames
               where each channel represents one 30-minute timestep.
        Returns:
            (B, out_channels, H, W) — predicted future precipitation frames
        """
        B, T, H, W = x.shape[0], x.shape[1], x.shape[2], x.shape[3]
        device = x.device

        h1, c1 = self.enc_cell1.init_hidden(B, H, W, device)
        h2, c2 = self.enc_cell2.init_hidden(B, H, W, device)

        # ── Encoder pass: process each input frame sequentially ──
        last_proj = None
        for t in range(T):
            frame = x[:, t:t+1, :, :]          # (B, 1, H, W)
            proj = self.input_proj(frame)        # (B, hidden, H, W)
            h1, c1 = self.enc_cell1(proj, h1, c1)
            h2, c2 = self.enc_cell2(h1, h2, c2)
            last_proj = proj

        # ── Decoder pass: autoregressively predict future frames ──
        dh1, dc1 = h1.clone(), c1.clone()
        dh2, dc2 = h2.clone(), c2.clone()
        inp = last_proj  # seed decoder with last encoded projection

        outputs = []
        for _ in range(self.out_channels):
            dh1, dc1 = self.dec_cell1(inp, dh1, dc1)
            dh2, dc2 = self.dec_cell2(dh1, dh2, dc2)
            pred = self.head(dh2)               # (B, 1, H, W)
            outputs.append(pred)
            inp = self.input_proj(pred)         # feed prediction back as next input

        return torch.cat(outputs, dim=1)        # (B, out_channels, H, W)

