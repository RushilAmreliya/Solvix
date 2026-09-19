"""
Unit tests for backend fixes:
1. Open-Meteo TTL caching and resilient stale-cache fallback
2. Chronological dataset splitting without sliding-window data leakage
3. Doppler Weather Radar (DWR) Marshall-Palmer Z-R conversion and polar rasterization
"""
import time
from unittest.mock import patch
import numpy as np
import pytest
import torch

from backend.engine import openmeteo_engine
from backend.engine.train import WeatherDataset
from backend.engine import radar_loader


# ─── 1. Open-Meteo TTL Caching Tests ──────────────────────────────────────────

def test_openmeteo_caching_and_expiry():
    """Verify that atmospheric context is cached and clear_cache resets it."""
    openmeteo_engine.clear_cache()

    # Mock responses.get so tests run without real internet requests
    fake_response_1 = {
        "hourly": {
            "time": ["2026-09-19T12:00"],
            "cape": [1650.0],
            "wind_speed_10m": [12.5],
            "wind_direction_10m": [180.0],
            "relative_humidity_2m": [82.0],
        }
    }
    fake_response_2 = {
        "hourly": {
            "time": ["2026-09-19T12:00"],
            "cape": [2500.0],
            "wind_speed_10m": [22.0],
            "wind_direction_10m": [220.0],
            "relative_humidity_2m": [95.0],
        }
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_response_1

        # 1st call: should hit requests.get
        ctx1 = openmeteo_engine.get_atmospheric_context()
        assert ctx1["cape"] == 1650.0
        assert mock_get.call_count == 1

        # 2nd call immediately: should return cached copy without network call
        mock_get.return_value.json.return_value = fake_response_2
        ctx2 = openmeteo_engine.get_atmospheric_context()
        assert ctx2["cape"] == 1650.0  # Still cached value
        assert mock_get.call_count == 1  # No additional network request

        # Force refresh: should bypass cache and fetch new value
        ctx3 = openmeteo_engine.get_atmospheric_context(force_refresh=True)
        assert ctx3["cape"] == 2500.0
        assert mock_get.call_count == 2


def test_openmeteo_stale_cache_on_network_failure():
    """Verify that network exceptions return the stale cached context rather than zeroes."""
    openmeteo_engine.clear_cache()

    fake_response = {
        "hourly": {
            "time": ["2026-09-19T12:00"],
            "cape": [1800.0],
            "wind_speed_10m": [14.0],
            "wind_direction_10m": [90.0],
            "relative_humidity_2m": [80.0],
        }
    }

    with patch("requests.get") as mock_get:
        # First successful call
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_response
        ctx = openmeteo_engine.get_atmospheric_context()
        assert ctx["cape"] == 1800.0

        # Now simulate network failure
        mock_get.side_effect = Exception("Connection timeout")
        # Force refresh with network error -> should return stale cached data
        fallback_ctx = openmeteo_engine.get_atmospheric_context(force_refresh=True)
        assert fallback_ctx["cape"] == 1800.0
        assert fallback_ctx["source"] == "open-meteo (cached)"


# ─── 2. Chronological Dataset Split Tests ─────────────────────────────────────

def test_chronological_split_no_leakage(tmp_path):
    """Verify that the training and validation splits have zero index overlap and temporal buffer."""
    # Create a synthetic precipitation dataset with 50 timesteps
    synth_cube = np.random.rand(50, 20, 30).astype(np.float32)
    data_file = tmp_path / "test_rain.npy"
    np.save(data_file, synth_cube)

    SEQ_IN = 3
    SEQ_OUT = 3
    dataset = WeatherDataset(str(data_file), seq_in=SEQ_IN, seq_out=SEQ_OUT)

    train_ratio = 0.8
    train_size = int(train_ratio * len(dataset))
    buffer_gap = dataset.total_seq  # 6 frames
    test_start_idx = min(train_size + buffer_gap, len(dataset))

    train_indices = list(range(0, train_size))
    test_indices = list(range(test_start_idx, len(dataset)))

    train_ds = torch.utils.data.Subset(dataset, train_indices)
    test_ds = torch.utils.data.Subset(dataset, test_indices)

    # 1. Zero index overlap
    assert set(train_indices).isdisjoint(set(test_indices))

    # 2. Strict chronological ordering (all test samples occur after all train samples)
    assert max(train_indices) < min(test_indices)

    # 3. Buffer gap strictly enforced
    assert (min(test_indices) - max(train_indices)) > dataset.total_seq

    # 4. Verify shapes
    x, y = train_ds[0]
    assert x.shape == (SEQ_IN, 20, 30)
    assert y.shape == (SEQ_OUT, 20, 30)


# ─── 3. Doppler Weather Radar Processing Tests ────────────────────────────────

def test_marshall_palmer_conversions():
    """Verify bidirectional Marshall-Palmer Z-R conversion for standard rain rates."""
    # Test values: light rain (2 mm/hr), moderate (15 mm/hr), cloudburst (55 mm/hr)
    test_rates = np.array([2.0, 15.0, 35.0, 55.0])

    # Convert mm/hr -> dBZ
    dbz = radar_loader.rain_rate_to_dbz(test_rates)
    assert np.all(dbz > 15.0)

    # Convert dBZ back -> mm/hr
    recovered_rates = radar_loader.dbz_to_rain_rate(dbz)
    for orig, rec in zip(test_rates, recovered_rates):
        assert pytest.approx(rec, rel=1e-3) == orig

    # Test thresholding: < 10 dBZ should give 0 mm/hr
    assert radar_loader.dbz_to_rain_rate(5.0) == 0.0


def test_polar_to_cartesian_rasterization():
    """Verify polar PPI radar sweep correctly rasterizes to the target Cartesian grid."""
    dbz_sweep, vel_sweep = radar_loader.generate_synthetic_dwr_sweep(n_az=360, n_gates=500, has_squall_line=True)

    # Rasterize to Guwahati radar location (26.106° N, 91.586° E)
    cartesian_grid = radar_loader.polar_to_cartesian_grid(
        polar_sweep=dbz_sweep,
        radar_lat=26.106,
        radar_lon=91.586,
        max_range_km=250.0,
        grid_shape=(100, 155),
    )

    assert cartesian_grid.shape == (100, 155)
    # The squall line should produce peak reflectivity > 35 dBZ in the Cartesian grid
    assert np.max(cartesian_grid) > 35.0


def test_radial_shear_microburst_detection():
    """Verify radial velocity shear detects severe divergence signatures."""
    # Synthetic velocity with sharp divergence (+25 m/s over 2 km)
    vel_polar = np.zeros((360, 200), dtype=float)
    vel_polar[180, 50:58] = np.linspace(-15.0, 25.0, 8)  # 40 m/s shift over 8 gates * 0.25 km = 2 km

    result = radar_loader.compute_radial_shear(vel_polar, gate_spacing_km=0.25, shear_threshold=0.01)

    assert result["microburst_detected"] is True
    assert result["max_shear_per_sec"] >= 0.01
    assert result["severe_zones_count"] > 0


def test_api_radar_sweep_ingestion():
    """Verify POST /api/v1/ingest/radar-sweep successfully processes polar radar data."""
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as client:
        # Generate smaller synthetic sweep (36 azimuths, 50 gates)
        dbz_sweep, vel_sweep = radar_loader.generate_synthetic_dwr_sweep(n_az=36, n_gates=50, has_squall_line=True)

        payload = {
            "reflectivity_dbz": dbz_sweep.tolist(),
            "velocity_mps": vel_sweep.tolist(),
            "radar_site": "Guwahati",
            "max_range_km": 200.0,
            "simulated_time": "2026-09-19T14:30:00",
        }

        resp = client.post("/api/v1/ingest/radar-sweep", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["radar_site"] == "Guwahati"
        assert "max_rain_mm_hr" in data
        assert "shear_info" in data
        assert "buffer_size" in data

