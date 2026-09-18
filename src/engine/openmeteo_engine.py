"""
Open-Meteo Atmospheric Context Engine
Fetches real wind, CAPE (storm energy), and humidity data.
No API key required — completely free and open-source.

API docs: https://open-meteo.com/en/docs
"""
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
ASSAM_LAT = 26.0
ASSAM_LON = 93.0

_FALLBACK = {
    "cape":           0.0,
    "wind_speed":     0.0,
    "wind_direction": 0.0,
    "humidity":       70.0,
    "source":         "fallback",
}


def fetch_atmospheric_context(lat: float = ASSAM_LAT, lon: float = ASSAM_LON) -> dict:
    """
    Fetch current atmospheric context from Open-Meteo.

    Returns dict with:
        cape           – Convective Available Potential Energy (J/kg). >1000 = active convection.
        wind_speed     – 10m wind speed (m/s)
        wind_direction – 10m wind direction (degrees)
        humidity       – 2m relative humidity (%)
        source         – 'open-meteo' or 'fallback'
    """
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
            return _FALLBACK.copy()

        # Find index closest to current UTC hour
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
        idx = 0
        for i, t in enumerate(times):
            if t >= now_str:
                idx = i
                break

        result = {
            "cape":           float(hourly.get("cape",                     [0])[idx] or 0),
            "wind_speed":     float(hourly.get("wind_speed_10m",           [0])[idx] or 0),
            "wind_direction": float(hourly.get("wind_direction_10m",       [0])[idx] or 0),
            "humidity":       float(hourly.get("relative_humidity_2m",    [70])[idx] or 70),
            "source":         "open-meteo",
        }
        logger.info(
            "Atmospheric context: CAPE=%.0f J/kg, Wind=%.1f m/s @ %.0f°, Humidity=%.0f%%",
            result["cape"], result["wind_speed"], result["wind_direction"], result["humidity"],
        )
        return result

    except Exception as exc:
        logger.warning("Open-Meteo fetch failed (%s) — using fallback zeros.", exc)
        return _FALLBACK.copy()


# Convenience alias used by main.py
def get_atmospheric_context() -> dict:
    return fetch_atmospheric_context(ASSAM_LAT, ASSAM_LON)


if __name__ == "__main__":
    import json
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = get_atmospheric_context()
    print(json.dumps(ctx, indent=2))
