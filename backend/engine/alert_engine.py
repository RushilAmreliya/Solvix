"""
NowCast Fusion — Model-Driven Alert Engine

Converts raw hazard arrays (from hazard_engine.py) + real atmospheric context
(from Open-Meteo via openmeteo_engine.py) + storm cell detections into structured,
human-readable alert objects following IMD severity colour codes.

Every alert is traceable to:
  1. A specific U-Net / PySTEPS forecast value
  2. A real measured atmospheric parameter (CAPE, wind speed, humidity)

IMD Severity Scale:
  GREEN  — No significant weather expected
  YELLOW — Be Aware (watch developing situation)
  ORANGE — Be Prepared (take precautionary action)
  RED    — Take Action (severe/extreme weather imminent)
"""
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ─── IMD / NDMA Thresholds ────────────────────────────────────────────────────
# Rain rate thresholds (mm/hr) for colour-coded alert levels
CLOUDBURST_RED    = 50.0   # IMD Cloudburst: ≥100 mm / 3 hr (≈50 mm/hr peak rate)
CLOUDBURST_ORANGE = 25.0   # Heavy to very heavy rain
CLOUDBURST_YELLOW = 10.0   # Moderate rain with convective risk

HAIL_RED          = 0.70   # Hail probability [0-1]
HAIL_ORANGE       = 0.45
HAIL_YELLOW       = 0.25

LIGHTNING_RED     = 0.65   # Lightning density index [0-1]
LIGHTNING_ORANGE  = 0.40
LIGHTNING_YELLOW  = 0.20

DOWNBURST_RED     = 0.75   # Downburst risk [0-1]
DOWNBURST_ORANGE  = 0.50
DOWNBURST_YELLOW  = 0.30

CAPE_EXTREME   = 2500.0    # J/kg — extreme convection
CAPE_HIGH      = 1500.0    # J/kg — high convection
CAPE_MODERATE  = 800.0     # J/kg — moderate convection
WIND_HIGH      = 15.0      # m/s  — elevated wind shear
HUMIDITY_HIGH  = 85.0      # %    — high moisture feed

# Key city names (must match hazard_engine.CITIES)
ASSAM_CITIES = ["Guwahati", "Dibrugarh", "Silchar", "Jorhat"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _severity_from_value(value: float, red: float, orange: float, yellow: float) -> str:
    """Map a scalar value to an IMD severity colour string."""
    if value >= red:
        return "RED"
    if value >= orange:
        return "ORANGE"
    if value >= yellow:
        return "YELLOW"
    return "GREEN"


def _cape_description(cape: float) -> str:
    if cape >= CAPE_EXTREME:
        return f"CAPE {cape:.0f} J/kg (extreme convection 🔴)"
    if cape >= CAPE_HIGH:
        return f"CAPE {cape:.0f} J/kg (high convection 🟠)"
    if cape >= CAPE_MODERATE:
        return f"CAPE {cape:.0f} J/kg (moderate convection 🟡)"
    return f"CAPE {cape:.0f} J/kg (stable)"


def _cities_near_hotspots(hazard_map: np.ndarray, threshold: float) -> list[str]:
    """
    Return city names whose nearest grid cells exceed threshold.
    Maps the 4 cities to approximate grid indices for a 100×155 Assam domain.
    """
    H, W = hazard_map.shape
    # Assam domain: lat 24.0–28.0, lon 89.8–96.0
    lat_min, lat_max = 24.0, 28.0
    lon_min, lon_max = 89.8, 96.0

    city_coords = {
        "Guwahati":  (26.14, 91.74),
        "Dibrugarh": (27.47, 94.91),
        "Silchar":   (24.82, 92.79),
        "Jorhat":    (26.75, 94.22),
    }

    affected = []
    for city, (lat, lon) in city_coords.items():
        # Map to grid index
        row = int((lat_max - lat) / (lat_max - lat_min) * (H - 1))
        col = int((lon - lon_min) / (lon_max - lon_min) * (W - 1))
        row = max(0, min(H - 1, row))
        col = max(0, min(W - 1, col))

        # Check a 5×5 neighbourhood
        r0, r1 = max(0, row - 2), min(H, row + 3)
        c0, c1 = max(0, col - 2), min(W, col + 3)
        if float(np.max(hazard_map[r0:r1, c0:c1])) >= threshold:
            affected.append(city)

    return affected


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def derive_alerts(
    hazards: dict[str, Any],
    atm_ctx: dict[str, float],
    storm_cells: list[dict],
    forecast_mm: np.ndarray,
) -> list[dict]:
    """
    Derive a list of structured alert objects from model outputs and live
    atmospheric measurements.

    Args:
        hazards:     Dict with keys cloudburst_risk, hail_probability,
                     lightning_density, downburst_risk — all (H,W) lists
        atm_ctx:     Dict with cape, wind_speed, wind_direction, humidity
        storm_cells: List of storm cell dicts from hazard_engine.get_storm_cells()
        forecast_mm: (n_leadtimes, H, W) precipitation forecast in mm/hr

    Returns:
        List of alert dicts, sorted by severity (RED first), each with:
          type, severity, title, reason, eta_minutes, affected_cities
    """
    alerts: list[dict] = []

    cape       = float(atm_ctx.get("cape", 0))
    wind_speed = float(atm_ctx.get("wind_speed", 0))
    humidity   = float(atm_ctx.get("humidity", 70))
    atm_source = atm_ctx.get("source", "fallback")

    # ── 1. Cloudburst ─────────────────────────────────────────────────────────
    cb_map = np.array(hazards.get("cloudburst_risk", [[0]]))
    cb_max = float(np.max(cb_map))
    # Also check raw mm/hr in the forecast for the reason string
    fc_max_30 = float(np.max(forecast_mm[0])) if forecast_mm.shape[0] > 0 else 0.0

    cb_severity = _severity_from_value(cb_max, 1.0, 0.5, 0.2)
    if cb_severity != "GREEN":
        affected = _cities_near_hotspots(cb_map, 0.4)
        city_str = f" near {', '.join(affected)}" if affected else " over Assam"

        reason_parts = [f"Model forecast: {fc_max_30:.1f} mm/hr at +30 min."]
        if cape >= CAPE_MODERATE:
            reason_parts.append(_cape_description(cape))
        if humidity >= HUMIDITY_HIGH:
            reason_parts.append(f"Humidity {humidity:.0f}% (high moisture feed).")

        alerts.append({
            "type": "cloudburst",
            "severity": cb_severity,
            "title": f"Cloudburst {'Warning' if cb_severity == 'RED' else 'Watch'}{city_str}",
            "reason": " ".join(reason_parts),
            "eta_minutes": 30,
            "affected_cities": affected,
        })

    # ── 2. Hail ───────────────────────────────────────────────────────────────
    hail_map = np.array(hazards.get("hail_probability", [[0]]))
    hail_max = float(np.max(hail_map))
    hail_severity = _severity_from_value(hail_max, HAIL_RED, HAIL_ORANGE, HAIL_YELLOW)

    if hail_severity != "GREEN":
        affected = _cities_near_hotspots(hail_map, HAIL_YELLOW)
        city_str = f" near {', '.join(affected)}" if affected else " over Assam"

        reason_parts = [f"Hail probability: {hail_max*100:.0f}% (model output)."]
        if cape >= CAPE_HIGH:
            reason_parts.append(f"{_cape_description(cape)} — deep convection supports large hail.")
        elif cape >= CAPE_MODERATE:
            reason_parts.append(_cape_description(cape))

        alerts.append({
            "type": "hail",
            "severity": hail_severity,
            "title": f"Hail {'Warning' if hail_severity == 'RED' else 'Watch'}{city_str}",
            "reason": " ".join(reason_parts),
            "eta_minutes": None,
            "affected_cities": affected,
        })

    # ── 3. Lightning ──────────────────────────────────────────────────────────
    lt_map = np.array(hazards.get("lightning_density", [[0]]))
    lt_max = float(np.max(lt_map))
    lt_severity = _severity_from_value(lt_max, LIGHTNING_RED, LIGHTNING_ORANGE, LIGHTNING_YELLOW)

    if lt_severity != "GREEN":
        affected = _cities_near_hotspots(lt_map, LIGHTNING_YELLOW)
        city_str = f" near {', '.join(affected)}" if affected else " over Assam"

        reason_parts = [f"Lightning density index: {lt_max*100:.0f}% (convective core >10 mm/hr)."]
        if humidity >= HUMIDITY_HIGH:
            reason_parts.append(f"Humidity {humidity:.0f}% — elevated moisture supports electrical activity.")
        if cape >= CAPE_MODERATE:
            reason_parts.append(_cape_description(cape))

        alerts.append({
            "type": "lightning",
            "severity": lt_severity,
            "title": f"Lightning Strike Zone{city_str}",
            "reason": " ".join(reason_parts),
            "eta_minutes": None,
            "affected_cities": affected,
        })

    # ── 4. Downburst / Microburst ─────────────────────────────────────────────
    db_map = np.array(hazards.get("downburst_risk", [[0]]))
    db_max = float(np.max(db_map))
    db_severity = _severity_from_value(db_max, DOWNBURST_RED, DOWNBURST_ORANGE, DOWNBURST_YELLOW)

    if db_severity != "GREEN":
        affected = _cities_near_hotspots(db_map, DOWNBURST_YELLOW)
        city_str = f" near {', '.join(affected)}" if affected else " over Assam"

        reason_parts = [f"Downburst risk: {db_max*100:.0f}% (intensity+gradient model output)."]
        if wind_speed >= WIND_HIGH:
            reason_parts.append(f"Surface wind: {wind_speed:.1f} m/s — wind shear amplifies microburst risk.")

        alerts.append({
            "type": "downburst",
            "severity": db_severity,
            "title": f"Downburst / Microburst {'Warning' if db_severity == 'RED' else 'Watch'}{city_str}",
            "reason": " ".join(reason_parts),
            "eta_minutes": None,
            "affected_cities": affected,
        })

    # ── 5. Storm Cell Arrival Alerts ──────────────────────────────────────────
    for cell in storm_cells:
        eta = int(cell.get("eta_minutes", 0))
        intensity = float(cell.get("intensity", 0))
        city = cell.get("city", "Unknown")

        if intensity >= 50.0:
            sev = "RED"
            label = "Extreme Cell"
        elif intensity >= 25.0:
            sev = "ORANGE"
            label = "Severe Cell"
        else:
            sev = "YELLOW"
            label = "Active Cell"

        alerts.append({
            "type": "storm_cell",
            "severity": sev,
            "title": f"⚡ {label} → {city} in {eta} min",
            "reason": (
                f"Storm cell intensity: {intensity:.1f} mm/hr. "
                f"ETA to {city}: {eta} minutes (U-Net + PySTEPS extrapolation). "
                + (_cape_description(cape) if cape >= CAPE_MODERATE else "")
            ),
            "eta_minutes": eta,
            "affected_cities": [city],
        })

    # ── 6. All-clear ──────────────────────────────────────────────────────────
    if not alerts:
        alerts.append({
            "type": "all_clear",
            "severity": "GREEN",
            "title": "✅ No Active Hazards — Assam Region",
            "reason": (
                f"All hazard indices below warning thresholds. "
                f"{_cape_description(cape)}. "
                f"Wind: {wind_speed:.1f} m/s. Humidity: {humidity:.0f}%. "
                f"Data source: {atm_source}."
            ),
            "eta_minutes": None,
            "affected_cities": [],
        })

    # Sort: RED → ORANGE → YELLOW → GREEN
    severity_order = {"RED": 0, "ORANGE": 1, "YELLOW": 2, "GREEN": 3}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

    logger.info(
        "Alert engine: %d alert(s) derived. Severities: %s",
        len(alerts),
        [a["severity"] for a in alerts],
    )
    return alerts
