"""
NowCast Fusion — IMD / MOSDAC Doppler Weather Radar Ingestion Engine

Provides native parsing, Quality Control (QC), and polar-to-Cartesian rasterization
for operational Doppler Weather Radar files conforming to:
  1. CF-Radial NetCDF-4 (WMO / IMD convention for Doppler sweeps)
  2. ODIM HDF5 (WMO standard OPERA / IMD DWR HDF5 exchange format)

Features:
  - Automatic format detection (.nc, .h5, .hdf5)
  - Clutter suppression & thresholding (min_dbz)
  - Standard IMD Marshall-Palmer Z-R conversion (Z = 200 * R^1.6)
  - Radial velocity shear & microburst divergence detection
  - Synthetic test file generators for automated verification
"""
import io
import logging
import os
import tempfile
from typing import Any

import numpy as np

from backend.engine import radar_loader

logger = logging.getLogger(__name__)

# Default regional grid domain (Assam: 100 x 155)
DEFAULT_GRID_SHAPE = (100, 155)


# ─── NetCDF (CF-Radial) Parser ────────────────────────────────────────────────

def parse_cf_radial_netcdf(file_path_or_bytes: str | bytes | io.BytesIO) -> dict[str, Any]:
    """
    Parse a CF-Radial NetCDF-4 radar file.
    Extracts reflectivity (DBZ), radial velocity (VEL), azimuths, and ranges.
    """
    import netCDF4 as nc

    temp_path = None
    if isinstance(file_path_or_bytes, (bytes, io.BytesIO)):
        data = file_path_or_bytes if isinstance(file_path_or_bytes, bytes) else file_path_or_bytes.getvalue()
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            tmp.write(data)
            temp_path = tmp.name
        ds = nc.Dataset(temp_path, "r")
    else:
        ds = nc.Dataset(file_path_or_bytes, "r")

    try:
        # Resolve reflectivity variable name
        dbz_var = None
        for name in ["DBZ", "REF", "reflectivity", "corrected_reflectivity", "CZ"]:
            if name in ds.variables:
                dbz_var = ds.variables[name]
                break

        if dbz_var is None:
            raise ValueError(f"No reflectivity variable found in NetCDF. Available: {list(ds.variables.keys())}")

        dbz_data = np.array(dbz_var[:], dtype=float)
        # Squeeze down to 2D (azimuth x range)
        if dbz_data.ndim > 2:
            dbz_data = dbz_data[0]

        # Resolve velocity variable
        vel_data = None
        for name in ["VEL", "VR", "velocity", "radial_velocity"]:
            if name in ds.variables:
                v = np.array(ds.variables[name][:], dtype=float)
                vel_data = v[0] if v.ndim > 2 else v
                break

        site_name = getattr(ds, "instrument_name", "Guwahati")
        max_range_km = 250.0
        if "range" in ds.variables:
            r_vals = ds.variables["range"][:]
            max_range_km = float(np.max(r_vals)) / 1000.0 if np.max(r_vals) > 1000 else float(np.max(r_vals))

        return {
            "format": "netcdf",
            "reflectivity_dbz": dbz_data,
            "velocity_mps": vel_data,
            "site_name": str(site_name),
            "max_range_km": max_range_km,
        }
    finally:
        ds.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ─── HDF5 (ODIM H5 / IMD DWR) Parser ──────────────────────────────────────────

def parse_odim_hdf5(file_path_or_bytes: str | bytes | io.BytesIO) -> dict[str, Any]:
    """
    Parse an ODIM HDF5 / IMD DWR radar sweep file.
    Extracts datasets from hierarchical groups (e.g. /dataset1/data1/data).
    """
    import h5py

    temp_path = None
    if isinstance(file_path_or_bytes, (bytes, io.BytesIO)):
        data = file_path_or_bytes if isinstance(file_path_or_bytes, bytes) else file_path_or_bytes.getvalue()
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            tmp.write(data)
            temp_path = tmp.name
        h5_file = h5py.File(temp_path, "r")
    else:
        h5_file = h5py.File(file_path_or_bytes, "r")

    try:
        dbz_data = None
        vel_data = None
        site_name = "Guwahati"

        if "how" in h5_file and "radar" in h5_file["how"].attrs:
            site_name = str(h5_file["how"].attrs["radar"])

        # Inspect dataset1
        if "dataset1" in h5_file:
            d1 = h5_file["dataset1"]
            if "data1" in d1 and "data" in d1["data1"]:
                raw_data = np.array(d1["data1"]["data"][:], dtype=float)
                # Check what quantity this is
                quant = "DBZH"
                if "what" in d1["data1"] and "quantity" in d1["data1"]["what"].attrs:
                    quant = str(d1["data1"]["what"].attrs["quantity"])
                
                # If gains and offsets are present in what group
                gain = 1.0
                offset = 0.0
                if "what" in d1["data1"]:
                    gain = float(d1["data1"]["what"].attrs.get("gain", 1.0))
                    offset = float(d1["data1"]["what"].attrs.get("offset", 0.0))
                
                scaled = raw_data * gain + offset

                if "DBZ" in quant.upper() or "CZ" in quant.upper():
                    dbz_data = scaled
                elif "VR" in quant.upper() or "VEL" in quant.upper():
                    vel_data = scaled

            # Check if dataset1/data2 or dataset2 contains radial velocity
            if "data2" in d1 and "data" in d1["data2"]:
                vel_data = np.array(d1["data2"]["data"][:], dtype=float)
            elif "dataset2" in h5_file and "data1" in h5_file["dataset2"]:
                vel_data = np.array(h5_file["dataset2"]["data1"]["data"][:], dtype=float)

        if dbz_data is None:
            raise ValueError("Could not find reflectivity dataset in ODIM HDF5 structure.")

        return {
            "format": "hdf5",
            "reflectivity_dbz": dbz_data,
            "velocity_mps": vel_data,
            "site_name": site_name,
            "max_range_km": 250.0,
        }
    finally:
        h5_file.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ─── Unified Processing Pipeline ──────────────────────────────────────────────

def process_radar_file(
    file_bytes_or_path: str | bytes | io.BytesIO,
    filename: str | None = None,
    grid_shape: tuple[int, int] = DEFAULT_GRID_SHAPE,
    default_site: str = "Guwahati",
) -> dict[str, Any]:
    """
    Ingests and processes a Doppler radar file (NetCDF or HDF5).
    
    Workflow:
      1. Detect format from filename or content.
      2. Extract polar sweep arrays (reflectivity + optional velocity).
      3. Quality control: Clutter & invalid values filter.
      4. Convert dBZ to rain rate (mm/hr) via Marshall-Palmer.
      5. Rasterize polar coordinates to Cartesian Assam regional grid.
      6. Calculate radial velocity shear if velocity data is available.

    Returns:
      Dictionary containing:
        - cartesian_rain: (H, W) ndarray in mm/hr
        - max_rain_mm_hr: float
        - max_dbz: float
        - site_name: str
        - format: str
        - shear_info: dict | None
    """
    fn = (filename or (file_bytes_or_path if isinstance(file_bytes_or_path, str) else "")).lower()

    if fn.endswith(".nc") or fn.endswith(".netcdf"):
        parsed = parse_cf_radial_netcdf(file_bytes_or_path)
    elif fn.endswith(".h5") or fn.endswith(".hdf5"):
        parsed = parse_odim_hdf5(file_bytes_or_path)
    else:
        # Try NetCDF first, fallback to HDF5
        try:
            parsed = parse_cf_radial_netcdf(file_bytes_or_path)
        except Exception:
            parsed = parse_odim_hdf5(file_bytes_or_path)

    dbz = parsed["reflectivity_dbz"]
    vel = parsed["velocity_mps"]
    site_name = parsed["site_name"] if parsed["site_name"] in radar_loader.IMD_DWR_SITES else default_site
    site_info = radar_loader.IMD_DWR_SITES.get(site_name, radar_loader.IMD_DWR_SITES[default_site])

    # Quality Control: replace NaNs / Inf with 0.0 dBZ
    dbz = np.nan_to_num(dbz, nan=0.0, posinf=75.0, neginf=-15.0)

    # Convert to rain rate (mm/hr)
    rain_polar = radar_loader.dbz_to_rain_rate(dbz)

    # Rasterize to Cartesian domain
    cartesian_rain = radar_loader.polar_to_cartesian_grid(
        polar_sweep=rain_polar,
        radar_lat=site_info["lat"],
        radar_lon=site_info["lon"],
        max_range_km=parsed["max_range_km"],
        grid_shape=grid_shape,
    )

    shear_info = None
    if vel is not None:
        vel = np.nan_to_num(vel, nan=0.0)
        shear_info = radar_loader.compute_radial_shear(vel)

    return {
        "status": "ok",
        "format": parsed["format"],
        "radar_site": site_name,
        "max_dbz": round(float(np.max(dbz)), 1),
        "max_rain_mm_hr": round(float(np.max(cartesian_rain)), 2),
        "cartesian_rain": cartesian_rain,
        "shear_info": shear_info,
    }


# ─── Synthetic Radar File Generators (For Testing / Offline CI) ───────────────

def generate_sample_cf_radial_netcdf(output_path: str, n_az: int = 72, n_gates: int = 100) -> str:
    """Generate a valid CF-Radial NetCDF file with a synthetic convective storm."""
    import netCDF4 as nc

    dbz_sweep, vel_sweep = radar_loader.generate_synthetic_dwr_sweep(n_az=n_az, n_gates=n_gates, has_squall_line=True)

    with nc.Dataset(output_path, "w", format="NETCDF4") as ds:
        ds.instrument_name = "Guwahati"
        ds.title = "IMD Doppler Weather Radar Level-II PPI Sweep"

        ds.createDimension("azimuth", n_az)
        ds.createDimension("range", n_gates)

        az_var = ds.createVariable("azimuth", "f4", ("azimuth",))
        rng_var = ds.createVariable("range", "f4", ("range",))
        dbz_var = ds.createVariable("DBZ", "f4", ("azimuth", "range"))
        vel_var = ds.createVariable("VEL", "f4", ("azimuth", "range"))

        az_var[:] = np.linspace(0, 360, n_az, endpoint=False, dtype=np.float32)
        rng_var[:] = np.linspace(1000, 250000, n_gates, dtype=np.float32)  # metres
        dbz_var[:] = np.ascontiguousarray(dbz_sweep, dtype=np.float32)
        vel_var[:] = np.ascontiguousarray(vel_sweep, dtype=np.float32)

    return output_path



def generate_sample_odim_hdf5(output_path: str, n_az: int = 72, n_gates: int = 100) -> str:
    """Generate a valid ODIM HDF5 radar file with a synthetic convective storm."""
    import h5py

    dbz_sweep, vel_sweep = radar_loader.generate_synthetic_dwr_sweep(n_az=n_az, n_gates=n_gates, has_squall_line=True)

    with h5py.File(output_path, "w") as f:
        how = f.create_group("how")
        how.attrs["radar"] = "Guwahati"

        d1 = f.create_group("dataset1")
        data1 = d1.create_group("data1")
        data1.create_dataset("data", data=dbz_sweep.astype(np.float32))
        what1 = data1.create_group("what")
        what1.attrs["quantity"] = "DBZH"
        what1.attrs["gain"] = 1.0
        what1.attrs["offset"] = 0.0

        data2 = d1.create_group("data2")
        data2.create_dataset("data", data=vel_sweep.astype(np.float32))
        what2 = data2.create_group("what")
        what2.attrs["quantity"] = "VRAD"

    return output_path
