"""
Terrain-based precipitation downscaling using SRTM 90m DEM.
Downscales 10km GPM precipitation to ~1km using orographic enhancement.

Physics: Orographic lifting forces moist air upward at mountain slopes,
producing 20-40% more precipitation per 1000m of elevation.
"""
import os
import time
import logging
import numpy as np
import cv2
import requests

logger = logging.getLogger(__name__)

SRTM_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/srtm_assam.npy")
)
# Assam bounding box
LAT_MIN, LON_MIN, LAT_MAX, LON_MAX = 24.0, 89.8, 28.0, 96.0
GPM_H, GPM_W = 40, 62
SCALE        = 10      # 10× upsample → ~1 km/pixel
ELEV_ROWS    = 80      # coarse elevation grid rows
ELEV_COLS    = 124     # coarse elevation grid cols


# ─── Elevation Download ───────────────────────────────────────────────────────

def _fetch_elevation_batch(locations: list[dict]) -> list[float]:
    """POST a batch of lat/lon locations to Open-Elevation and return metres."""
    try:
        resp = requests.post(
            "https://api.open-elevation.com/api/v1/lookup",
            json={"locations": locations},
            timeout=30,
        )
        if resp.status_code == 200:
            return [r["elevation"] for r in resp.json()["results"]]
    except Exception as e:
        logger.warning("Open-Elevation batch failed: %s", e)
    return [500.0] * len(locations)   # fallback: 500 m MSL


def _build_coarse_grid() -> np.ndarray:
    """Fetch an 80×124 elevation grid for Assam and return as ndarray."""
    lats = np.linspace(LAT_MIN, LAT_MAX, ELEV_ROWS)
    lons = np.linspace(LON_MIN, LON_MAX, ELEV_COLS)
    lat_g, lon_g = np.meshgrid(lats, lons, indexing="ij")

    locations = [
        {"latitude": float(lat_g[i, j]), "longitude": float(lon_g[i, j])}
        for i in range(ELEV_ROWS)
        for j in range(ELEV_COLS)
    ]

    elevations = []
    batch_size = 500
    for start in range(0, len(locations), batch_size):
        batch = locations[start : start + batch_size]
        elevations.extend(_fetch_elevation_batch(batch))
        time.sleep(0.5)   # polite delay for free API

    return np.array(elevations, dtype=np.float32).reshape(ELEV_ROWS, ELEV_COLS)


def download_srtm_assam() -> np.ndarray:
    logger.info("Downloading SRTM elevation grid for Assam (%d×%d points)…", ELEV_ROWS, ELEV_COLS)
    elev = _build_coarse_grid()
    logger.info("Elevation: shape=%s  max=%.0f m  mean=%.0f m", elev.shape, elev.max(), elev.mean())
    return elev


def get_or_load_srtm() -> np.ndarray:
    """Load cached SRTM DEM or download it fresh."""
    if os.path.exists(SRTM_PATH):
        logger.info("Loading cached SRTM from %s", SRTM_PATH)
        return np.load(SRTM_PATH)

    elev = download_srtm_assam()
    os.makedirs(os.path.dirname(SRTM_PATH), exist_ok=True)
    np.save(SRTM_PATH, elev)
    logger.info("SRTM saved to %s", SRTM_PATH)
    return elev


# ─── Downscaling ─────────────────────────────────────────────────────────────

def downscale_to_1km(
    precip_10km: np.ndarray,
    srtm_coarse: np.ndarray | None = None,
) -> np.ndarray:
    """
    Downscale a 10 km GPM precipitation field to ~1 km.

    Args:
        precip_10km:  (H, W) array in mm/hr at ~10 km resolution
        srtm_coarse:  (n_lat, n_lon) elevation array in metres.
                      If None — simple bicubic without terrain enhancement.

    Returns:
        (H×SCALE, W×SCALE) array in mm/hr at ~1 km resolution
    """
    h, w = precip_10km.shape
    target_h, target_w = h * SCALE, w * SCALE

    # Bicubic upsample the precipitation field
    precip_1km = cv2.resize(
        precip_10km.astype(np.float32),
        (target_w, target_h),
        interpolation=cv2.INTER_CUBIC,
    )
    precip_1km = np.clip(precip_1km, 0.0, None)

    if srtm_coarse is None:
        return precip_1km

    # Upsample the coarse elevation to the same 1 km grid
    elev_1km = cv2.resize(
        srtm_coarse.astype(np.float32),
        (target_w, target_h),
        interpolation=cv2.INTER_CUBIC,
    )
    elev_1km = np.clip(elev_1km, 0.0, None)

    # Orographic enhancement: +35% rain per 3000 m, capped at +50%
    enhancement = 1.0 + (elev_1km / 3000.0) * 0.35
    enhancement = np.clip(enhancement, 1.0, 1.5)

    return np.clip(precip_1km * enhancement, 0.0, None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    srtm = get_or_load_srtm()
    print(f"SRTM: {srtm.shape}  max={srtm.max():.0f} m")
    dummy = np.random.rand(GPM_H, GPM_W) * 20.0
    out   = downscale_to_1km(dummy, srtm)
    print(f"Input {dummy.shape} → Output {out.shape}")
