"""
NowCast Fusion — Hazard Products Engine

Converts raw precipitation forecasts into the 4 convective hazard products
required by SIH26084, using IMD standard thresholds and meteorological proxies.

Products:
    1. Cloudburst Risk     — IMD: ≥ 100 mm / 3 hrs  (≈ ≥ 50 mm/hr instantaneous)
    2. Hail Probability    — High convective intensity proxy (> 25 mm/hr)
    3. Lightning Density   — Convective core proxy (> 10 mm/hr)
    4. Downburst Risk      — High intensity + high spatial gradient
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# ─── Geographic Reference ─────────────────────────────────────────────────────
ASSAM_BOUNDS = {
    "lat_min": 24.0,
    "lat_max": 28.0,
    "lon_min": 89.8,
    "lon_max": 96.0,
}

# Key cities for storm ETA calculation
CITIES: dict[str, tuple[float, float]] = {
    "Guwahati":  (26.14, 91.74),
    "Dibrugarh": (27.47, 94.91),
    "Silchar":   (24.82, 92.79),
    "Jorhat":    (26.75, 94.22),
}

# ─── IMD / Meteorological Thresholds (mm/hr) ─────────────────────────────────
CLOUDBURST_THRESHOLD = 50.0   # ~100 mm in 3 hrs → IMD cloudburst criterion
HAIL_THRESHOLD       = 25.0   # High convective intensity → hail-prone environment
LIGHTNING_THRESHOLD  = 10.0   # Convective core threshold for CG lightning activity
DOWNBURST_THRESHOLD  = 20.0   # High-intensity region for microburst risk


# ─── Coordinate Helpers ───────────────────────────────────────────────────────

def _grid_to_latlon(H: int, W: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (lat_grid, lon_grid) of shape (H, W) for the Assam bounding box."""
    lats = np.linspace(ASSAM_BOUNDS["lat_max"], ASSAM_BOUNDS["lat_min"], H)
    lons = np.linspace(ASSAM_BOUNDS["lon_min"], ASSAM_BOUNDS["lon_max"], W)
    return np.meshgrid(lats, lons, indexing="ij")  # (H, W)


# ─── Hazard Product Functions ─────────────────────────────────────────────────

def compute_cloudburst_risk(precip_mm_hr: np.ndarray) -> np.ndarray:
    """
    Cloudburst risk map [0–1].

    IMD definition: ≥ 100 mm of rain in ≤ 3 hours, equivalent to a sustained
    instantaneous rate of ≥ 33 mm/hr; we use 50 mm/hr as the upper anchor
    to account for peak-rate events.

    Args:
        precip_mm_hr: (H, W) precipitation in mm/hr
    Returns:
        (H, W) float array of cloudburst probability [0–1]
    """
    risk = np.clip(precip_mm_hr / CLOUDBURST_THRESHOLD, 0.0, 1.0)
    return risk.astype(float)


def compute_hail_probability(precip_mm_hr: np.ndarray) -> np.ndarray:
    """
    Hail probability map [0–1].

    Proxy: In a pre-monsoon or active convective environment, GPM rain rates
    above 25 mm/hr are strongly correlated with deep convective cells
    capable of producing hail (cf. Cecil & Zipser 2002).

    Args:
        precip_mm_hr: (H, W) precipitation in mm/hr
    Returns:
        (H, W) float array of hail probability [0–1]
    """
    prob = np.clip(
        (precip_mm_hr - HAIL_THRESHOLD) / HAIL_THRESHOLD,
        0.0, 1.0,
    )
    return prob.astype(float)


def compute_lightning_density(precip_mm_hr: np.ndarray) -> np.ndarray:
    """
    Lightning strike density index [0–1].

    Proxy: Ground-level CG lightning strongly correlates with the vertical
    extent of convective updrafts, which is proxied by high rain rates.
    Convective cores above 10 mm/hr are treated as electrically active.

    Args:
        precip_mm_hr: (H, W) precipitation in mm/hr
    Returns:
        (H, W) float array of lightning density index [0–1]
    """
    span = CLOUDBURST_THRESHOLD - LIGHTNING_THRESHOLD
    density = np.clip(
        (precip_mm_hr - LIGHTNING_THRESHOLD) / span,
        0.0, 1.0,
    )
    return density.astype(float)


def compute_downburst_risk(precip_mm_hr: np.ndarray) -> np.ndarray:
    """
    Downburst / microburst risk map [0–1].

    Proxy: Microbursts occur in areas of high precipitation intensity combined
    with a sharp spatial gradient — indicating rapid localized downdrafts at
    the edge of a collapsing convective cell.

    Risk = 0.6 × intensity_component + 0.4 × gradient_component

    Args:
        precip_mm_hr: (H, W) precipitation in mm/hr
    Returns:
        (H, W) float array of downburst risk [0–1]
    """
    try:
        from scipy.ndimage import uniform_filter
        smoothed = uniform_filter(precip_mm_hr.astype(float), size=3)
    except ImportError:
        smoothed = precip_mm_hr  # Degrade gracefully

    gradient      = np.abs(precip_mm_hr.astype(float) - smoothed)
    intensity_risk = np.clip(precip_mm_hr / DOWNBURST_THRESHOLD, 0.0, 1.0)
    gradient_risk  = np.clip(gradient / 5.0, 0.0, 1.0)

    risk = 0.6 * intensity_risk + 0.4 * gradient_risk
    return risk.astype(float)


# ─── Spatial Feature Extraction ───────────────────────────────────────────────

def get_hazard_polygons(
    hazard_map: np.ndarray,
    threshold: float = 0.4,
    max_polygons: int = 20,
) -> list[dict]:
    """
    Convert a hazard probability map to a list of GeoJSON-ready polygon features.

    Each polygon encloses a connected high-risk region above `threshold`.
    Polygons are represented as bounding-box rectangles in geographic coordinates.

    Args:
        hazard_map:   (H, W) float array of risk [0–1]
        threshold:    Minimum risk level to trigger a polygon
        max_polygons: Cap on number of polygons returned (largest risk first)
    Returns:
        list of dicts with keys: centroid_lat, centroid_lon, risk, bounds
    """
    try:
        from scipy.ndimage import label
    except ImportError:
        logger.warning("scipy not available — skipping polygon generation.")
        return []

    H, W = hazard_map.shape
    lat_grid, lon_grid = _grid_to_latlon(H, W)

    binary, n_features = label((hazard_map >= threshold).astype(int))

    polygons = []
    for region_idx in range(1, n_features + 1):
        mask = binary == region_idx
        avg_risk      = float(np.mean(hazard_map[mask]))
        centroid_lat  = float(np.mean(lat_grid[mask]))
        centroid_lon  = float(np.mean(lon_grid[mask]))
        region_lats   = lat_grid[mask]
        region_lons   = lon_grid[mask]

        polygons.append({
            "centroid_lat": round(centroid_lat, 3),
            "centroid_lon": round(centroid_lon, 3),
            "risk": round(avg_risk, 3),
            "bounds": [
                [float(region_lats.max()), float(region_lons.min())],
                [float(region_lats.max()), float(region_lons.max())],
                [float(region_lats.min()), float(region_lons.max())],
                [float(region_lats.min()), float(region_lons.min())],
            ],
        })

    # Sort by risk descending and cap
    polygons.sort(key=lambda p: p["risk"], reverse=True)
    return polygons[:max_polygons]


def get_storm_cells(
    precip_forecast: np.ndarray,
    motion_field: np.ndarray | None = None,
    dt_minutes: float = 30.0,
) -> list[dict]:
    """
    Detect storm cells from the forecast and estimate arrival ETA at key cities.

    For each city, check if a convective cell (> LIGHTNING_THRESHOLD) is present
    in the forecast window. ETA is the lead time of the first forecast frame
    that shows significant rain near the city.

    Args:
        precip_forecast: (n_leadtimes, H, W) forecast in mm/hr
        motion_field:    (2, H, W) motion vectors or None (unused, reserved)
        dt_minutes:      Minutes between consecutive forecast frames
    Returns:
        list of {"city", "eta_minutes", "intensity", "lat", "lon"} dicts
    """
    n_lt, H, W = precip_forecast.shape
    lat_grid, lon_grid = _grid_to_latlon(H, W)
    results = []

    for city_name, (city_lat, city_lon) in CITIES.items():
        # Nearest grid cell to the city
        dist = np.sqrt((lat_grid - city_lat) ** 2 + (lon_grid - city_lon) ** 2)
        ci, cj = np.unravel_index(np.argmin(dist), dist.shape)

        # Search radius of 3 grid cells around the city
        r = 3
        i0, i1 = max(0, ci - r), min(H, ci + r + 1)
        j0, j1 = max(0, cj - r), min(W, cj + r + 1)

        for lt in range(n_lt):
            local_rain     = precip_forecast[lt, i0:i1, j0:j1]
            max_intensity  = float(np.max(local_rain))

            if max_intensity >= LIGHTNING_THRESHOLD:
                eta_min = (lt + 1) * dt_minutes
                results.append({
                    "city":        city_name,
                    "eta_minutes": int(eta_min),
                    "intensity":   round(max_intensity, 1),
                    "lat":         city_lat,
                    "lon":         city_lon,
                })
                break  # Use earliest threatening lead time for this city

    return results
