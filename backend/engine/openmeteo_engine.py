"""
Open-Meteo Atmospheric Context Engine
Fetches real wind, CAPE (storm energy), and humidity data.
No API key required — completely free and open-source.

API docs: https://open-meteo.com/en/docs
"""
import logging
import threading
import time
from datetime import datetime, timezone
import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
ASSAM_LAT = 26.0
ASSAM_LON = 93.0
CACHE_TTL_SECONDS = 900.0  # 15 minutes TTL

_FALLBACK = {
    "cape":           0.0,
    "wind_speed":     0.0,
    "wind_direction": 0.0,
    "humidity":       70.0,
    "source":         "fallback",
}

# ─── Thread-Safe In-Memory Cache ──────────────────────────────────────────────
_cache_lock = threading.Lock()
_cached_data: dict | None = None
_cached_timestamp: float = 0.0


def clear_cache() -> None:
    """Clear atmospheric context cache (used in tests or manual reset)."""
    global _cached_data, _cached_timestamp
    with _cache_lock:
        _cached_data = None
        _cached_timestamp = 0.0


def fetch_atmospheric_context(
    lat: float = ASSAM_LAT,
    lon: float = ASSAM_LON,
    force_refresh: bool = False,
) -> dict:
    """
    Fetch current atmospheric context from Open-Meteo with 15-minute TTL caching.

    Returns dict with:
        cape           – Convective Available Potential Energy (J/kg). >1000 = active convection.
        wind_speed     – 10m wind speed (m/s)
        wind_direction – 10m wind direction (degrees)
        humidity       – 2m relative humidity (%)
        source         – 'open-meteo', 'open-meteo (cached)', or 'fallback'
    """
    global _cached_data, _cached_timestamp

    now = time.time()
    with _cache_lock:
        if not force_refresh and _cached_data is not None:
            age = now - _cached_timestamp
            if age < CACHE_TTL_SECONDS:
                logger.debug("Returning cached atmospheric context (age: %.1f s)", age)
                return _cached_data.copy()

    try:
        resp = requests.get(
            API_URL,
            params={
                "latitude":  lat,
                "longitude": lon,
                "hourly":    "cape,wind_speed_10m,wind_direction_10m,relative_humidity_2m",
                "forecast_days": 1,
                "timezone":  "auto",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        hourly = data.get("hourly", {})
        times  = hourly.get("time", [])

        if not times:
            with _cache_lock:
                if _cached_data is not None:
                    stale = _cached_data.copy()
                    stale["source"] = "open-meteo (cached)"
                    return stale
            return _FALLBACK.copy()

        # Find index closest to current UTC hour
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
        idx = 0
        for i, t in enumerate(times):
            if t >= now_str:
                idx = i
                break

        result = {
            "cape":           float(hourly.get("cape",                  [0])[idx] or 0),
            "wind_speed":     float(hourly.get("wind_speed_10m",        [0])[idx] or 0),
            "wind_direction": float(hourly.get("wind_direction_10m",    [0])[idx] or 0),
            "humidity":       float(hourly.get("relative_humidity_2m", [70])[idx] or 70),
            "source":         "open-meteo",
        }

        with _cache_lock:
            _cached_data = result
            _cached_timestamp = time.time()

        logger.info(
            "Atmospheric context updated: CAPE=%.0f J/kg, Wind=%.1f m/s @ %.0f°, Humidity=%.0f%%",
            result["cape"], result["wind_speed"], result["wind_direction"], result["humidity"],
        )
        return result.copy()

    except Exception as exc:
        with _cache_lock:
            if _cached_data is not None:
                logger.warning("Open-Meteo fetch failed (%s) — using stale cached data.", exc)
                stale = _cached_data.copy()
                stale["source"] = "open-meteo (cached)"
                return stale

        logger.warning("Open-Meteo fetch failed (%s) — using fallback zeroes.", exc)
        return _FALLBACK.copy()


# Convenience alias used by main.py
def get_atmospheric_context(force_refresh: bool = False) -> dict:
    return fetch_atmospheric_context(ASSAM_LAT, ASSAM_LON, force_refresh=force_refresh)


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    ctx = get_atmospheric_context()
    print(json.dumps(ctx, indent=2))
