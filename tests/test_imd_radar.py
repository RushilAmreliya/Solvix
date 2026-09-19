"""
Tests for IMD / MOSDAC Doppler Radar ingestion:
  1. CF-Radial NetCDF parsing and polar-to-Cartesian rasterization
  2. ODIM HDF5 radar file parsing and Z-R conversion
  3. POST /api/v1/ingest/radar-file API endpoint via TestClient
"""
import io
import os
import tempfile

import numpy as np
import pytest

from backend.engine import radar_loader
from backend.engine.imd_radar_loader import (
    generate_sample_cf_radial_netcdf,
    generate_sample_odim_hdf5,
    parse_cf_radial_netcdf,
    parse_odim_hdf5,
    process_radar_file,
)


# ─── 1. CF-Radial NetCDF Tests ────────────────────────────────────────────────

def test_cf_radial_netcdf_generation_and_parse(tmp_path):
    """Generate a synthetic CF-Radial NetCDF and verify parsing extracts DBZ data."""
    nc_path = str(tmp_path / "test_sweep.nc")
    generate_sample_cf_radial_netcdf(nc_path, n_az=36, n_gates=50)

    assert os.path.exists(nc_path), "NetCDF file was not created"

    parsed = parse_cf_radial_netcdf(nc_path)
    assert parsed["format"] == "netcdf"
    assert parsed["reflectivity_dbz"].ndim == 2
    assert parsed["reflectivity_dbz"].shape == (36, 50)
    assert parsed["velocity_mps"] is not None
    assert parsed["velocity_mps"].shape == (36, 50)
    assert parsed["site_name"] == "Guwahati"


def test_cf_radial_netcdf_polar_to_cartesian(tmp_path):
    """Verify that CF-Radial data rasterizes correctly to 100×155 Cartesian domain."""
    nc_path = str(tmp_path / "test_sweep_full.nc")
    generate_sample_cf_radial_netcdf(nc_path, n_az=72, n_gates=100)

    result = process_radar_file(nc_path, filename="test_sweep_full.nc", grid_shape=(100, 155))

    assert result["status"] == "ok"
    assert result["format"] == "netcdf"
    assert result["cartesian_rain"].shape == (100, 155)
    assert result["max_rain_mm_hr"] >= 0.0
    assert result["max_dbz"] >= 0.0


def test_cf_radial_shear_detection(tmp_path):
    """Verify that radial velocity shear is detected from CF-Radial data."""
    nc_path = str(tmp_path / "test_shear.nc")
    generate_sample_cf_radial_netcdf(nc_path, n_az=36, n_gates=50)

    result = process_radar_file(nc_path, filename="test_shear.nc", grid_shape=(100, 155))

    # shear_info should be present since velocity data was included
    assert "shear_info" in result
    # shear_info should be a dict with microburst detection key
    if result["shear_info"] is not None:
        assert "microburst_detected" in result["shear_info"]


# ─── 2. ODIM HDF5 Tests ───────────────────────────────────────────────────────

def test_odim_hdf5_generation_and_parse(tmp_path):
    """Generate a synthetic ODIM HDF5 and verify parsing extracts DBZ data."""
    h5_path = str(tmp_path / "test_dwr.h5")
    generate_sample_odim_hdf5(h5_path, n_az=36, n_gates=50)

    assert os.path.exists(h5_path), "HDF5 file was not created"

    parsed = parse_odim_hdf5(h5_path)
    assert parsed["format"] == "hdf5"
    assert parsed["reflectivity_dbz"].ndim == 2
    assert parsed["reflectivity_dbz"].shape == (36, 50)
    assert parsed["velocity_mps"] is not None
    assert parsed["site_name"] == "Guwahati"


def test_odim_hdf5_polar_to_cartesian(tmp_path):
    """Verify that ODIM HDF5 data rasterizes correctly to the Assam Cartesian domain."""
    h5_path = str(tmp_path / "test_dwr_full.h5")
    generate_sample_odim_hdf5(h5_path, n_az=72, n_gates=100)

    result = process_radar_file(h5_path, filename="test_dwr_full.h5", grid_shape=(100, 155))

    assert result["status"] == "ok"
    assert result["format"] == "hdf5"
    assert result["cartesian_rain"].shape == (100, 155)
    assert result["max_rain_mm_hr"] >= 0.0


def test_auto_format_detection_netcdf(tmp_path):
    """Verify format auto-detection selects NetCDF for .nc extension."""
    nc_path = str(tmp_path / "auto_detect.nc")
    generate_sample_cf_radial_netcdf(nc_path, n_az=36, n_gates=50)

    result = process_radar_file(nc_path, filename="auto_detect.nc")
    assert result["format"] == "netcdf"


def test_auto_format_detection_hdf5(tmp_path):
    """Verify format auto-detection selects HDF5 for .h5 extension."""
    h5_path = str(tmp_path / "auto_detect.h5")
    generate_sample_odim_hdf5(h5_path, n_az=36, n_gates=50)

    result = process_radar_file(h5_path, filename="auto_detect.h5")
    assert result["format"] == "hdf5"


def test_nan_qc_handling(tmp_path):
    """Verify that NaN / Inf values in reflectivity are handled gracefully (QC pass)."""
    import netCDF4 as nc

    nc_path = str(tmp_path / "nan_test.nc")
    generate_sample_cf_radial_netcdf(nc_path, n_az=36, n_gates=50)

    # Inject NaN values into the file
    with nc.Dataset(nc_path, "a") as ds:
        arr = ds.variables["DBZ"][:]
        arr[0, :] = float("nan")
        arr[1, :] = float("inf")
        ds.variables["DBZ"][:] = arr

    # Should not raise, QC should replace NaN/Inf with valid values
    result = process_radar_file(nc_path, filename="nan_test.nc")
    assert result["status"] == "ok"
    assert not np.any(np.isnan(result["cartesian_rain"]))
    assert not np.any(np.isinf(result["cartesian_rain"]))


# ─── 3. API Endpoint Test ─────────────────────────────────────────────────────

def test_api_radar_file_upload_netcdf(tmp_path):
    """POST /api/v1/ingest/radar-file should accept a CF-Radial NetCDF file."""
    from fastapi.testclient import TestClient
    from backend.main import app

    nc_path = str(tmp_path / "upload_test.nc")
    generate_sample_cf_radial_netcdf(nc_path, n_az=36, n_gates=50)

    with open(nc_path, "rb") as f:
        content = f.read()

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingest/radar-file",
            files={"file": ("upload_test.nc", content, "application/octet-stream")},
            data={"radar_site": "Guwahati"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["format"] == "netcdf"
    assert data["radar_site"] == "Guwahati"
    assert "max_rain_mm_hr" in data
    assert "buffer_size" in data
    assert data["buffer_size"] > 0


def test_api_radar_file_upload_hdf5(tmp_path):
    """POST /api/v1/ingest/radar-file should accept an ODIM HDF5 file."""
    from fastapi.testclient import TestClient
    from backend.main import app

    h5_path = str(tmp_path / "upload_test.h5")
    generate_sample_odim_hdf5(h5_path, n_az=36, n_gates=50)

    with open(h5_path, "rb") as f:
        content = f.read()

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingest/radar-file",
            files={"file": ("upload_test.h5", content, "application/octet-stream")},
            data={"radar_site": "Guwahati"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["format"] == "hdf5"
