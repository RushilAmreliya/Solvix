"""
NowCast Fusion — Live Radar Ingestion Engine

Fetches real-time composite Doppler Weather Radar (DWR) and satellite-radar frames
from the open RainViewer API, crops and rasterizes them to the Assam regional domain,
and converts radar reflectivity (dBZ) into precipitation intensity (mm/hr)
via the IMD standard Marshall-Palmer Z-R relationship.

This ensures the entire nowcasting analysis pipeline (PySTEPS optical flow,
U-Net intensity correction, hazard engine, alert engine) analyzes REAL LIVE
weather radar data happening right now instead of historical simulations.

Domain Bounds (Assam, North-East India):
    Lat: 24.0°N to 28.0°N
    Lon: 89.8°E to 96.0°E
    Grid: (100, 155) float32 array in mm/hr
"""
import io
import logging
import math
import time
from typing import Any

import numpy as np
from PIL import Image
import requests

logger = logging.getLogger(__name__)

RAINVIEWER_MANIFEST_URL = "https://api.rainviewer.com/public/weather-maps.json"

# Target domain specification
LAT_MIN = 24.0
LAT_MAX = 28.0
LON_MIN = 89.8
LON_MAX = 96.0
TARGET_H = 100
TARGET_W = 155
ZOOM_LEVEL = 6

# IMD Marshall-Palmer constants
MP_A = 200.0
MP_B = 1.6

# Global state for tracking last ingested live radar timestamp
_last_ingested_timestamp: int = 0
_cached_live_sequence: list[tuple[int, np.ndarray]] = []


# ─── Coordinate & Tile Transformations ────────────────────────────────────────

def latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Convert (lat, lon) in degrees to fractional tile coordinates (x, y) at zoom."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def get_assam_tile_ranges(zoom: int = ZOOM_LEVEL) -> dict[str, int]:
    """Calculate the tile index bounding box covering the Assam domain."""
    x_min, y_max_tile = latlon_to_tile(LAT_MIN, LON_MIN, zoom)
    x_max, y_min_tile = latlon_to_tile(LAT_MAX, LON_MAX, zoom)
    return {
        "x_start": int(math.floor(x_min)),
        "x_end": int(math.floor(x_max)),
        "y_start": int(math.floor(y_min_tile)),
        "y_end": int(math.floor(y_max_tile)),
    }


# ─── Radar Reflectivity (dBZ) to Rain Rate Conversion ─────────────────────────

def rgba_to_rain_rate(rgba_img: np.ndarray) -> np.ndarray:
    """
    Convert an RGBA radar tile composite to rain rate in mm/hr.
    
    1. Transparent pixels (alpha < 20) = 0.0 mm/hr.
    2. Uses perceptual luminance and chromaticity of standard radar palettes
       to estimate equivalent reflectivity factor (dBZ: 10 to 70 dBZ).
    3. Converts dBZ to mm/hr using Marshall-Palmer Z = 200 * R^1.6.
    """
    alpha = rgba_img[..., 3]
    mask = alpha > 20
    rain_rate = np.zeros(alpha.shape, dtype=np.float32)

    if not mask.any():
        return rain_rate

    r = rgba_img[..., 0].astype(np.float32)
    g = rgba_img[..., 1].astype(np.float32)
    b = rgba_img[..., 2].astype(np.float32)

    # Perceptual luminance proxy
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    # Base reflectivity: 10 dBZ (light drizzle) to 60 dBZ (heavy storm)
    est_dbz = 10.0 + (luminance / 255.0) * 50.0

    # Red-dominant boost for severe convective cores (dBZ > 45)
    red_excess = np.clip((r - g) / 255.0, 0.0, 1.0) * 15.0
    est_dbz += red_excess
    est_dbz = np.clip(est_dbz, 10.0, 72.0)

    # Marshall-Palmer Z = 200 * R^1.6  =>  R = (10^(dBZ / 10) / 200)^(1 / 1.6)
    z = 10.0 ** (est_dbz[mask] / 10.0)
    rain_rate[mask] = (z / MP_A) ** (1.0 / MP_B)

    return rain_rate


# ─── Live Radar Ingestion ─────────────────────────────────────────────────────

def fetch_live_radar_frame(
    host: str,
    frame_path: str,
    session: requests.Session | None = None,
) -> np.ndarray:
    """
    Download the 6 radar tiles covering Assam, stitch, crop, and resample
    into a (100, 155) float32 precipitation array in mm/hr.
    """
    close_session = False
    if session is None:
        session = requests.Session()
        close_session = True

    try:
        bounds = get_assam_tile_ranges(ZOOM_LEVEL)
        x_start, x_end = bounds["x_start"], bounds["x_end"]
        y_start, y_end = bounds["y_start"], bounds["y_end"]

        n_x = x_end - x_start + 1
        n_y = y_end - y_start + 1

        stitched = Image.new("RGBA", (n_x * 256, n_y * 256), (0, 0, 0, 0))

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                url = f"{host}{frame_path}/256/{ZOOM_LEVEL}/{x}/{y}/0/0_0.png"
                try:
                    resp = session.get(url, timeout=5)
                    if resp.status_code == 200:
                        tile = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                        stitched.paste(tile, ((x - x_start) * 256, (y - y_start) * 256))
                except Exception as exc:
                    logger.debug("Failed fetching tile (%d, %d): %s", x, y, exc)

        # Precise pixel cropping coordinates within stitched image
        def to_stitched_px(lat: float, lon: float) -> tuple[float, float]:
            gx, gy = latlon_to_tile(lat, lon, ZOOM_LEVEL)
            return (gx - x_start) * 256.0, (gy - y_start) * 256.0

        x_left, y_top = to_stitched_px(LAT_MAX, LON_MIN)
        x_right, y_bottom = to_stitched_px(LAT_MIN, LON_MAX)

        cropped = stitched.crop((x_left, y_top, x_right, y_bottom))
        resized = cropped.resize((TARGET_W, TARGET_H), Image.Resampling.BILINEAR)

        rgba_arr = np.array(resized)
        rain_grid = rgba_to_rain_rate(rgba_arr)
        return rain_grid

    finally:
        if close_session:
            session.close()


def fetch_live_radar_sequence(
    n_frames: int = 3,
) -> list[tuple[int, np.ndarray]]:
    """
    Query RainViewer for recent radar frames and download the last n_frames
    (typically 10-minute intervals) covering Assam.

    Returns:
        List of (timestamp, rain_grid_100x155) tuples in chronological order.
    """
    try:
        resp = requests.get(RAINVIEWER_MANIFEST_URL, timeout=8)
        resp.raise_for_status()
        manifest = resp.json()

        host = manifest.get("host", "https://tilecache.rainviewer.com")
        past_frames = manifest.get("radar", {}).get("past", [])

        if not past_frames:
            logger.warning("No past radar frames found in RainViewer manifest.")
            return []

        selected = past_frames[-n_frames:]
        results: list[tuple[int, np.ndarray]] = []

        with requests.Session() as session:
            for frame_info in selected:
                ts = frame_info["time"]
                path = frame_info["path"]
                logger.info("Fetching live radar frame: time=%s path=%s", ts, path)
                grid = fetch_live_radar_frame(host, path, session=session)
                results.append((ts, grid))

        return results

    except Exception as exc:
        logger.warning("Failed to fetch live radar sequence from RainViewer: %s", exc)
        return []


def sync_live_radar_into_buffer(
    frame_buffer: Any,
    min_frames: int = 3,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """
    Synchronize real live radar frames into the backend's frame_buffer.

    - If buffer has fewer than min_frames or force_refresh is True:
      Fetches the last 3 chronological live radar sweeps (t-20m, t-10m, t).
    - If buffer already has live data:
      Checks for a newer radar sweep. If available, appends it.

    Returns:
        Dict with status, source, timestamp, max_rain_mm_hr, and buffer_size.
    """
    global _last_ingested_timestamp

    now_ts = int(time.time())

    # Case 1: Initial buffer fill or forced refresh
    if len(frame_buffer) < min_frames or force_refresh:
        logger.info("Seeding frame buffer with live radar sequence (%d frames)...", min_frames)
        seq = fetch_live_radar_sequence(n_frames=min_frames)
        if seq:
            frame_buffer.clear()
            for ts, grid in seq:
                frame_buffer.append(grid)
                _last_ingested_timestamp = ts
            max_rain = float(np.max(seq[-1][1]))
            logger.info(
                "Live radar sequence seeded: %d frames, latest ts=%d, max_rain=%.2f mm/hr",
                len(seq), _last_ingested_timestamp, max_rain
            )
            return {
                "status": "seeded",
                "source": "live-radar",
                "timestamp": _last_ingested_timestamp,
                "max_rain_mm_hr": max_rain,
                "buffer_size": len(frame_buffer),
            }

    # Case 2: Incremental update check
    try:
        resp = requests.get(RAINVIEWER_MANIFEST_URL, timeout=5)
        if resp.status_code == 200:
            manifest = resp.json()
            host = manifest.get("host", "https://tilecache.rainviewer.com")
            past = manifest.get("radar", {}).get("past", [])
            if past:
                latest = past[-1]
                latest_ts = latest["time"]
                if latest_ts > _last_ingested_timestamp:
                    logger.info("New live radar frame detected (ts=%d > %d). Ingesting...",
                                latest_ts, _last_ingested_timestamp)
                    grid = fetch_live_radar_frame(host, latest["path"])
                    frame_buffer.append(grid)
                    _last_ingested_timestamp = latest_ts
                    max_rain = float(np.max(grid))
                    return {
                        "status": "updated",
                        "source": "live-radar",
                        "timestamp": latest_ts,
                        "max_rain_mm_hr": max_rain,
                        "buffer_size": len(frame_buffer),
                    }
    except Exception as exc:
        logger.debug("Incremental live radar check failed: %s", exc)

    latest_rain = float(np.max(frame_buffer[-1])) if frame_buffer else 0.0
    return {
        "status": "current",
        "source": "live-radar" if _last_ingested_timestamp > 0 else "simulator",
        "timestamp": _last_ingested_timestamp or now_ts,
        "max_rain_mm_hr": latest_rain,
        "buffer_size": len(frame_buffer),
    }
