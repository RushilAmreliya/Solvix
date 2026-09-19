"""
Tests for UNet architecture, skill score metrics, and FastAPI test client.
"""
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from backend.engine.nowcast_model import UNetNowcast
from backend.engine.train import compute_csi, compute_ets
from backend.main import app


def test_unet_output_shape():
    """UNet forward pass should preserve spatial dimensions and produce non-negative values."""
    model = UNetNowcast(in_channels=3, out_channels=3, features=16)
    # Batch size 2, 3 channels, 40 height, 64 width (multiples of 8 for 3 poolings)
    dummy_input = torch.rand(2, 3, 40, 64)
    output = model(dummy_input)

    assert output.shape == (2, 3, 40, 64)
    assert torch.all(output >= 0.0)  # Non-negative precipitation head


def test_csi_and_ets_perfect_score():
    """Identical predictions and targets should yield CSI = 1.0 and ETS = 1.0."""
    target = np.array([0.0, 0.0, 0.5, 0.8, 1.0])
    pred = target.copy()

    csi = compute_csi(pred, target, threshold=0.1)
    ets = compute_ets(pred, target, threshold=0.1)

    assert pytest.approx(csi, rel=1e-3) == 1.0
    assert pytest.approx(ets, rel=1e-3) == 1.0


def test_csi_and_ets_zero_skill():
    """Completely incorrect predictions should yield CSI = 0.0."""
    target = np.array([0.0, 0.0, 0.5, 0.8, 1.0])
    pred = np.array([0.0, 0.0, 0.0, 0.0, 0.0])

    csi = compute_csi(pred, target, threshold=0.1)
    assert csi == 0.0


def test_api_health_endpoint():
    """GET / should return 200 and health dictionary."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


def test_api_ingest_and_forecast_flow():
    """POST /api/v1/ingest/frame followed by GET /api/v1/forecast/latest should succeed."""
    with TestClient(app) as client:
        # Send 3 dummy frames
        dummy_frame = np.zeros((40, 62)).tolist()
        dummy_frame[20][30] = 15.0

        for i in range(3):
            ingest_res = client.post(
                "/api/v1/ingest/frame",
                json={"frame": dummy_frame, "simulated_time": f"2023-05-15 12:{i*30:02d}"},
            )
            assert ingest_res.status_code == 200
            assert ingest_res.json()["status"] == "ok"

        # Now get latest forecast
        forecast_res = client.get("/api/v1/forecast/latest")
        assert forecast_res.status_code == 200
        fc = forecast_res.json()
        assert "images" in fc
        assert "hazards" in fc
        assert "current" in fc["images"]
        assert "cloudburst" in fc["images"]
        assert "atmospheric_context" in fc
        assert "alerts" in fc
        assert isinstance(fc["alerts"], list)
        assert len(fc["alerts"]) > 0
        assert "severity" in fc["alerts"][0]
        assert "title" in fc["alerts"][0]
        assert "reason" in fc["alerts"][0]


def test_alert_engine_severe_convection():
    """Alert engine should generate RED/ORANGE alerts when extreme rain and CAPE are present."""
    from backend.engine.alert_engine import derive_alerts

    H, W = 100, 155
    cloudburst_risk = np.zeros((H, W))
    cloudburst_risk[45:50, 70:75] = 1.0  # Near Guwahati

    hazards = {
        "cloudburst_risk": cloudburst_risk.tolist(),
        "hail_probability": np.zeros((H, W)).tolist(),
        "lightning_density": np.zeros((H, W)).tolist(),
        "downburst_risk": np.zeros((H, W)).tolist(),
    }
    atm_ctx = {
        "cape": 2600.0,
        "wind_speed": 18.0,
        "humidity": 90.0,
        "source": "test",
    }
    forecast_mm = np.zeros((12, H, W))
    forecast_mm[0, 45:50, 70:75] = 60.0

    alerts = derive_alerts(hazards, atm_ctx, [], forecast_mm)
    assert len(alerts) > 0
    severities = [a["severity"] for a in alerts]
    assert "RED" in severities
    red_alert = next(a for a in alerts if a["severity"] == "RED")
    assert "Cloudburst" in red_alert["title"]
    assert "CAPE" in red_alert["reason"]


def test_alert_engine_all_clear():
    """Alert engine should return a single GREEN all-clear alert when conditions are benign."""
    from backend.engine.alert_engine import derive_alerts

    H, W = 100, 155
    hazards = {
        "cloudburst_risk": np.zeros((H, W)).tolist(),
        "hail_probability": np.zeros((H, W)).tolist(),
        "lightning_density": np.zeros((H, W)).tolist(),
        "downburst_risk": np.zeros((H, W)).tolist(),
    }
    atm_ctx = {
        "cape": 200.0,
        "wind_speed": 4.0,
        "humidity": 65.0,
        "source": "test",
    }
    forecast_mm = np.zeros((12, H, W))

    alerts = derive_alerts(hazards, atm_ctx, [], forecast_mm)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "GREEN"
    assert "No Active Hazards" in alerts[0]["title"]
