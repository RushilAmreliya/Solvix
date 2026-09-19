"""
NowCast Fusion — Doppler Weather Radar (DWR) Processing Engine

Implements ingestion, coordinate transformations, and meteorological conversions
for Doppler Weather Radar sweeps conforming to India Meteorological Department (IMD)
and WMO standards.

Key Meteorological Capabilities:
  1. Marshall-Palmer Z-R Relationship:
     Z = a * R^b  (IMD standard: a = 200, b = 1.6 for continental convection)
     R = (10^(dBZ / 10) / a) ^ (1 / b)
  2. Polar-to-Cartesian Rasterization:
     Converts PPI (Plan Position Indicator) range-azimuth sweeps (r, theta)
     to georeferenced Cartesian latitude-longitude grids.
  3. Doppler Radial Velocity Shear / Divergence:
     Detects microburst and downburst signatures from radial velocity gradients (dV_r / dr).
  4. Radar Sweep Simulation / Ingestion:
     Produces or ingests radar sweeps (dBZ & m/s) mapped to the Assam domain.
"""
import logging
import math
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ─── Standard IMD / WMO Radar Constants ───────────────────────────────────────
MARSHALL_PALMER_A = 200.0   # Convective/stratiform coefficient
MARSHALL_PALMER_B = 1.6     # Exponent

# Typical IMD DWR Sites in North-East India
IMD_DWR_SITES = {
    "Guwahati":    {"lat": 26.106, "lon": 91.586, "elevation_m": 54, "band": "S-Band"},
    "Mohanbari":   {"lat": 27.483, "lon": 95.017, "elevation_m": 110, "band": "C-Band"},
    "Cherrapunji": {"lat": 25.298, "lon": 91.733, "elevation_m": 1313, "band": "S-Band"},
    "Agartala":    {"lat": 23.887, "lon": 91.240, "elevation_m": 15, "band": "C-Band"},
}

# Regional domain bounding box (Assam / NE India)
ASSAM_BOUNDS = {
    "lat_min": 24.0,
    "lat_max": 28.0,
    "lon_min": 89.8,
    "lon_max": 96.0,
}


# ─── Marshall-Palmer Z-R Conversions ──────────────────────────────────────────

def dbz_to_rain_rate(
    dbz: np.ndarray | float,
    a: float = MARSHALL_PALMER_A,
    b: float = MARSHALL_PALMER_B,
    min_dbz: float = 10.0,
) -> np.ndarray | float:
    """
    Convert equivalent radar reflectivity factor (dBZ) to rain rate (mm/hr)
    using the standard Marshall-Palmer relation: Z = a * R^b.

    Args:
        dbz: Reflectivity in dBZ (scalar or NumPy array).
        a:   Empirical coefficient (default 200.0).
        b:   Empirical exponent (default 1.6).
        min_dbz: Reflectivity threshold below which rain rate is considered 0.

    Returns:
        Rain rate in mm/hr.
    """
    is_scalar = np.isscalar(dbz)
    dbz_arr = np.asarray(dbz, dtype=float)

    # Z = 10^(dBZ / 10) [mm^6 / m^3]
    # R = (Z / a) ^ (1 / b)
    z_linear = np.power(10.0, np.clip(dbz_arr, -30.0, 80.0) / 10.0)
    rain_rate = np.power(z_linear / a, 1.0 / b)

    # Suppress below threshold (clutter / non-meteorological echo)
    rain_rate = np.where(dbz_arr >= min_dbz, rain_rate, 0.0)

    return float(rain_rate) if is_scalar else rain_rate


def rain_rate_to_dbz(
    rain_rate: np.ndarray | float,
    a: float = MARSHALL_PALMER_A,
    b: float = MARSHALL_PALMER_B,
    min_rain: float = 0.05,
) -> np.ndarray | float:
    """
    Convert rain rate (mm/hr) to radar reflectivity (dBZ):
    Z = a * R^b  =>  dBZ = 10 * log10(a * R^b).

    Args:
        rain_rate: Rain rate in mm/hr.
        a: Empirical coefficient (default 200.0).
        b: Empirical exponent (default 1.6).
        min_rain: Minimum rain rate to avoid log(0).

    Returns:
        Reflectivity in dBZ.
    """
    is_scalar = np.isscalar(rain_rate)
    r_arr = np.asarray(rain_rate, dtype=float)

    # Handle zero/very low rain gracefully
    valid_mask = r_arr >= min_rain
    safe_r = np.where(valid_mask, r_arr, min_rain)

    z = a * np.power(safe_r, b)
    dbz = 10.0 * np.log10(np.clip(z, 1e-3, None))
    dbz = np.where(valid_mask, dbz, -15.0)

    return float(dbz) if is_scalar else dbz


# ─── Polar to Cartesian Rasterization ─────────────────────────────────────────

def polar_to_cartesian_grid(
    polar_sweep: np.ndarray,
    radar_lat: float,
    radar_lon: float,
    max_range_km: float = 250.0,
    grid_shape: tuple[int, int] = (100, 155),
    bounds: dict[str, float] = ASSAM_BOUNDS,
    fill_value: float = 0.0,
) -> np.ndarray:
    """
    Rasterize a polar PPI radar sweep (azimuth, range) onto a regular lat/lon
    Cartesian grid covering the specified geographic bounding box.

    Args:
        polar_sweep:  2-D array of shape (n_azimuths, n_gates).
        radar_lat:    Latitude of radar site (degrees N).
        radar_lon:    Longitude of radar site (degrees E).
        max_range_km: Maximum instrumented range in kilometers.
        grid_shape:   Target (H, W) of the output grid.
        bounds:       Bounding box dict with lat_min, lat_max, lon_min, lon_max.
        fill_value:   Value for grid cells beyond radar range or below threshold.

    Returns:
        (H, W) Cartesian array of rasterized radar data.
    """
    H, W = grid_shape
    n_az, n_gates = polar_sweep.shape

    lats = np.linspace(bounds["lat_max"], bounds["lat_min"], H)
    lons = np.linspace(bounds["lon_min"], bounds["lon_max"], W)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")

    # Great-circle approximation for regional scale (equirectangular projection)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(radar_lat))

    dy_km = (lat_grid - radar_lat) * km_per_deg_lat
    dx_km = (lon_grid - radar_lon) * km_per_deg_lon

    # Distance r from radar in km
    r_km = np.sqrt(dx_km ** 2 + dy_km ** 2)

    # Meteorological azimuth: clockwise from North (0° = North, 90° = East)
    az_deg = np.degrees(np.arctan2(dx_km, dy_km)) % 360.0

    # Map (r, az) to matrix indices in polar_sweep
    gate_idx = (r_km / max_range_km * (n_gates - 1)).astype(int)
    az_idx   = (az_deg / 360.0 * n_az).astype(int)

    # Valid mask within radar range
    in_range = (r_km <= max_range_km) & (gate_idx >= 0) & (gate_idx < n_gates) & (az_idx >= 0) & (az_idx < n_az)

    cartesian = np.full((H, W), fill_value, dtype=float)
    cartesian[in_range] = polar_sweep[az_idx[in_range], gate_idx[in_range]]

    return cartesian


# ─── Radial Velocity Microburst Shear Analysis ────────────────────────────────

def compute_radial_shear(
    velocity_polar: np.ndarray,
    gate_spacing_km: float = 0.25,
    shear_threshold: float = 0.01,
) -> dict[str, Any]:
    """
    Compute radial velocity shear dV_r / dr from Doppler velocity sweeps.

    A strong positive gradient along the radial line (outbound velocity
    increasing with distance) indicates diverging outflow — the hallmark signature
    of a wet or dry microburst / downburst touching down.

    Args:
        velocity_polar: (n_azimuth, n_gates) Doppler velocity in m/s.
        gate_spacing_km: Distance between successive range gates.
        shear_threshold: Shear threshold in s^-1 (10^-2 s^-1 is severe microburst).

    Returns:
        dict with:
            max_shear_per_sec: Peak radial shear value (s^-1)
            microburst_detected: Boolean flag
            severe_zones_count: Number of gates exceeding threshold
    """
    # Gradient along range dimension (axis 1)
    # dv in m/s, dr in meters: (dV / dr) * (1 / (gate_spacing_km * 1000))
    dv = np.diff(velocity_polar, axis=1)
    dr_m = gate_spacing_km * 1000.0
    shear = dv / dr_m  # unit: s^-1

    max_shear = float(np.max(shear)) if shear.size > 0 else 0.0
    severe_mask = shear >= shear_threshold
    count = int(np.sum(severe_mask))

    return {
        "max_shear_per_sec": round(max_shear, 5),
        "microburst_detected": max_shear >= shear_threshold,
        "severe_zones_count": count,
    }


# ─── Synthetic Sweep Generator (for offline testing & demo) ───────────────────

def generate_synthetic_dwr_sweep(
    n_az: int = 360,
    n_gates: int = 500,
    has_squall_line: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a physically realistic pair of synthetic DWR sweeps:
      - Reflectivity sweep (dBZ)
      - Doppler radial velocity sweep (m/s)

    Args:
        n_az: Number of azimuthal rays (1 ray per degree = 360).
        n_gates: Number of range gates (500 gates @ 0.5 km = 250 km).
        has_squall_line: If True, injects an intense convective squall line.

    Returns:
        (reflectivity_dbz, radial_velocity_mps)
    """
    dbz = np.full((n_az, n_gates), -10.0, dtype=float)
    vel = np.zeros((n_az, n_gates), dtype=float)

    if has_squall_line:
        # Create a curved squall line propagating east-southeast
        az_angles = np.linspace(0, 360, n_az, endpoint=False)
        range_km  = np.linspace(0, 250, n_gates)

        for i, az in enumerate(az_angles):
            # Squall band centered between 200° and 320° azimuth, range 60-120 km
            if 180 <= az <= 340:
                center_r = 90.0 + 25.0 * math.sin(math.radians(az - 180))
                dist = np.abs(range_km - center_r)
                cell_intensity = 55.0 * np.exp(-(dist ** 2) / (2 * 12.0 ** 2))
                dbz[i] = np.maximum(dbz[i], cell_intensity - 10.0)

                # Velocity dipole: strong inbound to strong outbound across convective core
                # Outbound: +25 m/s, Inbound: -20 m/s
                v_signature = 30.0 * np.tanh((range_km - center_r) / 8.0)
                vel[i] = np.where(dist < 30.0, v_signature, 0.0)

    return dbz, vel
