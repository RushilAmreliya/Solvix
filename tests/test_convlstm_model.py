"""
Tests for ConvLSTMNowcast spatiotemporal model and MultiYearWeatherDataset:
  1. ConvLSTMCell forward pass shape & hidden state
  2. ConvLSTMNowcast forward pass shape, non-negative output, gradient flow
  3. MultiYearWeatherDataset chunk aggregation and normalisation
"""
import os
import tempfile

import numpy as np
import pytest
import torch

from backend.engine.nowcast_model import ConvLSTMCell, ConvLSTMNowcast, UNetNowcast


# ─── 1. ConvLSTMCell Tests ────────────────────────────────────────────────────

def test_convlstm_cell_output_shape():
    """ConvLSTMCell should produce h and c of correct shape."""
    cell = ConvLSTMCell(in_channels=16, hidden_channels=32)
    B, H, W = 2, 20, 24
    x = torch.rand(B, 16, H, W)
    h, c = cell.init_hidden(B, H, W, torch.device("cpu"))
    h_new, c_new = cell(x, h, c)

    assert h_new.shape == (B, 32, H, W), f"h shape mismatch: {h_new.shape}"
    assert c_new.shape == (B, 32, H, W), f"c shape mismatch: {c_new.shape}"


def test_convlstm_cell_init_hidden_zeros():
    """ConvLSTMCell.init_hidden should return zero tensors of correct shape."""
    cell = ConvLSTMCell(in_channels=8, hidden_channels=16)
    h, c = cell.init_hidden(batch_size=3, height=10, width=12, device=torch.device("cpu"))
    assert torch.all(h == 0.0), "Initial hidden state should be zero"
    assert torch.all(c == 0.0), "Initial cell state should be zero"
    assert h.shape == (3, 16, 10, 12)


# ─── 2. ConvLSTMNowcast Tests ─────────────────────────────────────────────────

def test_convlstm_nowcast_output_shape():
    """ConvLSTMNowcast forward pass should preserve spatial dimensions."""
    model = ConvLSTMNowcast(in_channels=3, out_channels=3, hidden_channels=16)
    # Use dimensions divisible by nothing special (ConvLSTM has no pooling)
    x = torch.rand(2, 3, 20, 30)
    out = model(x)

    assert out.shape == (2, 3, 20, 30), f"Output shape mismatch: {out.shape}"


def test_convlstm_nowcast_non_negative():
    """ConvLSTMNowcast output must be non-negative (physical precipitation constraint)."""
    model = ConvLSTMNowcast(in_channels=3, out_channels=3, hidden_channels=16)
    model.eval()
    with torch.no_grad():
        x = torch.rand(2, 3, 20, 30)
        out = model(x)
    assert torch.all(out >= 0.0), "Precipitation output contains negative values"


def test_convlstm_nowcast_gradient_flows():
    """ConvLSTMNowcast should compute valid gradients through the full graph."""
    model = ConvLSTMNowcast(in_channels=3, out_channels=3, hidden_channels=16)
    x = torch.rand(1, 3, 20, 30, requires_grad=False)
    target = torch.rand(1, 3, 20, 30)

    out = model(x)
    loss = torch.nn.functional.mse_loss(out, target)
    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"Gradient is None for parameter: {name}"
        assert not torch.any(torch.isnan(param.grad)), f"NaN gradient in: {name}"


def test_convlstm_nowcast_irregular_spatial_dims():
    """ConvLSTMNowcast should handle arbitrary (non-power-of-2) spatial dimensions."""
    model = ConvLSTMNowcast(in_channels=3, out_channels=3, hidden_channels=16)
    model.eval()
    with torch.no_grad():
        # Typical operational grid: 100×155
        x = torch.rand(1, 3, 100, 155)
        out = model(x)
    assert out.shape == (1, 3, 100, 155)


def test_convlstm_vs_unet_same_interface():
    """ConvLSTMNowcast and UNetNowcast should share the same forward-pass interface."""
    for ModelClass in [UNetNowcast, ConvLSTMNowcast]:
        model = ModelClass(in_channels=3, out_channels=3)
        model.eval()
        with torch.no_grad():
            x = torch.rand(1, 3, 40, 62)
            out = model(x)
        assert out.shape == (1, 3, 40, 62), (
            f"{ModelClass.__name__} output shape mismatch: {out.shape}"
        )
        assert torch.all(out >= 0.0), f"{ModelClass.__name__} produced negative outputs"


# ─── 3. MultiYearWeatherDataset Tests ────────────────────────────────────────

def test_multi_year_dataset_single_chunk(tmp_path):
    """MultiYearWeatherDataset should load a single chunk correctly."""
    from backend.engine.train import MultiYearWeatherDataset

    cube = (np.random.rand(50, 20, 30) * 30).astype(np.float32)
    chunk_path = tmp_path / "assam_persiann_4km_smart_chunk_2023.npy"
    np.save(str(chunk_path), cube)

    ds = MultiYearWeatherDataset(str(tmp_path), seq_in=3, seq_out=3)
    assert len(ds) == max(0, 50 - 6)
    assert ds.max_val > 0.0

    x, y = ds[0]
    assert x.shape == (3, 20, 30)
    assert y.shape == (3, 20, 30)


def test_multi_year_dataset_multiple_chunks(tmp_path):
    """MultiYearWeatherDataset should concatenate multiple annual chunks."""
    from backend.engine.train import MultiYearWeatherDataset

    for year, n_frames in [(2023, 40), (2024, 30), (2025, 20)]:
        cube = (np.random.rand(n_frames, 20, 30) * 25).astype(np.float32)
        np.save(str(tmp_path / f"assam_persiann_4km_smart_chunk_{year}.npy"), cube)

    ds = MultiYearWeatherDataset(str(tmp_path), seq_in=3, seq_out=3)

    # Total frames = 40 + 30 + 20 = 90; samples = 90 - 6 = 84
    assert len(ds) == max(0, 90 - 6), f"Expected 84 samples, got {len(ds)}"

    x, y = ds[0]
    assert x.shape == (3, 20, 30)
    assert y.shape == (3, 20, 30)

    # All values should be normalised in [0, 1]
    assert float(x.max()) <= 1.0 + 1e-5, "Normalisation failed — values > 1.0"
    assert float(y.min()) >= 0.0, "Normalisation failed — negative values"


def test_multi_year_dataset_global_normalisation(tmp_path):
    """Global max normalisation should be consistent across all chunks."""
    from backend.engine.train import MultiYearWeatherDataset

    # Chunk 1: max = 20, Chunk 2: max = 50 (global max)
    cube1 = (np.ones((20, 10, 10)) * 20).astype(np.float32)
    cube2 = (np.ones((20, 10, 10)) * 50).astype(np.float32)
    np.save(str(tmp_path / "assam_persiann_4km_smart_chunk_2023.npy"), cube1)
    np.save(str(tmp_path / "assam_persiann_4km_smart_chunk_2024.npy"), cube2)

    ds = MultiYearWeatherDataset(str(tmp_path), seq_in=3, seq_out=3)

    assert ds.max_val == pytest.approx(50.0, rel=1e-3), (
        f"Expected global max of 50.0, got {ds.max_val}"
    )

    x, _ = ds[0]
    # Frames from chunk 1 are 20/50 = 0.4 normalised
    assert float(x.max()) == pytest.approx(0.4, rel=1e-3)


def test_multi_year_dataset_fallback_to_combined(tmp_path):
    """MultiYearWeatherDataset falls back to assam_persiann_4km.npy if no chunks exist."""
    from backend.engine.train import MultiYearWeatherDataset

    cube = (np.random.rand(30, 10, 10) * 20).astype(np.float32)
    np.save(str(tmp_path / "assam_persiann_4km.npy"), cube)

    ds = MultiYearWeatherDataset(str(tmp_path), seq_in=3, seq_out=3)
    assert len(ds) == max(0, 30 - 6)


def test_multi_year_dataset_missing_data_raises(tmp_path):
    """MultiYearWeatherDataset should raise FileNotFoundError if no data is available."""
    from backend.engine.train import MultiYearWeatherDataset

    with pytest.raises(FileNotFoundError):
        MultiYearWeatherDataset(str(tmp_path), seq_in=3, seq_out=3)
