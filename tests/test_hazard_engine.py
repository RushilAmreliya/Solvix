"""
Unit tests for backend.engine.hazard_engine
Tests IMD thresholds, proxy conversions, CAPE/wind enhancements, and polygon generation.
"""
import numpy as np
import pytest
from backend.engine import hazard_engine


def test_compute_cloudburst_risk():
    """Cloudburst risk should be 0 at 0 mm/hr and 1.0 at >= 50 mm/hr."""
    precip = np.array([
        [0.0, 25.0],
        [50.0, 100.0]
    ])
    risk = hazard_engine.compute_cloudburst_risk(precip)

    assert risk.shape == precip.shape
    assert risk[0, 0] == 0.0
    assert pytest.approx(risk[0, 1], rel=1e-3) == 0.5
    assert risk[1, 0] == 1.0
    assert risk[1, 1] == 1.0  # Clipped to 1.0


def test_compute_hail_probability_baseline():
    """Hail probability should be 0 for rain <= 25 mm/hr and scale up to 1.0 at 50 mm/hr."""
    precip = np.array([
        [10.0, 25.0],
        [37.5, 50.0]
    ])
    prob = hazard_engine.compute_hail_probability(precip, cape=0.0)

    assert prob[0, 0] == 0.0
    assert prob[0, 1] == 0.0
    assert pytest.approx(prob[1, 0], rel=1e-3) == 0.5
    assert prob[1, 1] == 1.0


def test_compute_hail_probability_with_cape():
    """High CAPE (>1000 J/kg) should amplify hail probability up to 1.5x."""
    precip = np.array([[37.5]])  # Baseline without CAPE is 0.5
    prob_no_cape = hazard_engine.compute_hail_probability(precip, cape=500.0)
    prob_high_cape = hazard_engine.compute_hail_probability(precip, cape=2000.0)

    assert pytest.approx(prob_no_cape[0, 0], rel=1e-3) == 0.5
    # CAPE=2000 adds factor 1.0 + 1.0 * 0.5 = 1.5x => 0.5 * 1.5 = 0.75
    assert pytest.approx(prob_high_cape[0, 0], rel=1e-3) == 0.75


def test_compute_lightning_density():
    """Lightning index should be 0 below 10 mm/hr and 1.0 at 50 mm/hr."""
    precip = np.array([
        [5.0, 10.0],
        [30.0, 50.0]
    ])
    density = hazard_engine.compute_lightning_density(precip)

    assert density[0, 0] == 0.0
    assert density[0, 1] == 0.0
    assert pytest.approx(density[1, 0], rel=1e-3) == 0.5  # (30-10)/(50-10) = 20/40 = 0.5
    assert density[1, 1] == 1.0


def test_compute_downburst_risk_wind_shear():
    """Downburst risk should incorporate gradient and surface wind speed."""
    precip = np.ones((10, 10)) * 10.0
    # Add a sharp spike in the middle to create a high gradient
    precip[4:6, 4:6] = 30.0

    risk_calm = hazard_engine.compute_downburst_risk(precip, wind_speed=5.0)
    risk_gale = hazard_engine.compute_downburst_risk(precip, wind_speed=25.0)

    # Gale winds (>15 m/s) should strictly increase downburst risk
    assert np.all(risk_gale >= risk_calm)
    assert np.max(risk_gale) <= 1.0


def test_get_hazard_polygons():
    """Polygon extraction should identify connected components above threshold."""
    hmap = np.zeros((40, 62), dtype=float)
    # Put a high risk region
    hmap[10:15, 20:25] = 0.85

    polys = hazard_engine.get_hazard_polygons(hmap, threshold=0.5)
    assert len(polys) == 1
    poly = polys[0]
    assert poly["risk"] == 0.85
    assert "centroid_lat" in poly
    assert "centroid_lon" in poly
    assert len(poly["bounds"]) == 4


def test_get_storm_cells_detection():
    """Storm cells should calculate ETA for threatened cities."""
    # 12 lead times, 40x62 grid
    fc = np.zeros((12, 40, 62), dtype=float)

    # Guwahati is at ~ (26.14 N, 91.74 E)
    # Inject heavy rain cell at Guwahati at leadtime index 1 (+60 min)
    # Let's see city coordinates mapping:
    lat_grid, lon_grid = hazard_engine._grid_to_latlon(40, 62)
    dist = (lat_grid - 26.14)**2 + (lon_grid - 91.74)**2
    ci, cj = np.unravel_index(np.argmin(dist), dist.shape)

    fc[1, ci, cj] = 35.0  # Cell arrives at leadtime 1 => (1+1)*30 = 60 min

    cells = hazard_engine.get_storm_cells(fc)
    guwahati_alert = [c for c in cells if c["city"] == "Guwahati"]
    assert len(guwahati_alert) == 1
    assert guwahati_alert[0]["eta_minutes"] == 60
    assert guwahati_alert[0]["intensity"] == 35.0
