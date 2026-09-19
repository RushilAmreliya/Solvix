"""
Unit tests for backend.engine.pysteps_engine
Tests precipitation unit transformations and persistence fallback.
"""
import numpy as np
import pytest
from backend.engine import pysteps_engine


def test_mm_to_dbr_roundtrip():
    """Converting mm/hr -> dBR -> mm/hr should recover positive precipitation values accurately."""
    original_rain = np.array([0.0, 0.05, 1.0, 15.0, 50.0, 100.0], dtype=float)
    dbr = pysteps_engine._mm_to_dbr(original_rain)
    recovered_rain = pysteps_engine._dbr_to_mm(dbr)

    # Values below 0.1 mm/hr are zeroed out by design
    assert recovered_rain[0] == 0.0
    assert recovered_rain[1] == 0.0

    # Values >= 0.1 mm/hr should match closely
    for i in range(2, len(original_rain)):
        assert pytest.approx(recovered_rain[i], rel=1e-3) == original_rain[i]


def test_persistence_forecast():
    """Persistence forecast should repeat the latest frame n_leadtimes times."""
    frame = np.random.rand(20, 30) * 20.0
    fc = pysteps_engine._persistence_forecast(frame, n_leadtimes=5)

    assert fc.shape == (5, 20, 30)
    for i in range(5):
        np.testing.assert_array_equal(fc[i], frame)


def test_run_optical_flow_persistence_fallback():
    """If given fewer than 2 frames, optical flow should cleanly fall back to persistence."""
    single_frame_stack = np.random.rand(1, 20, 30) * 15.0
    fc, motion = pysteps_engine.run_optical_flow(single_frame_stack, n_leadtimes=3)

    assert fc.shape == (3, 20, 30)
    assert motion is None
    np.testing.assert_array_equal(fc[0], single_frame_stack[0])
