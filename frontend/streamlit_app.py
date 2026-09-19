"""
NowCast Fusion — Streamlit Dashboard
Real-time Convective Hazard Early Warning System for North-East India (Assam Region).

Features:
    - Auto-refresh every 30 seconds
    - Precipitation forecast maps: Current / +30 / +60 / +90 min tabs
    - 4 hazard product maps: Cloudburst / Hail / Lightning / Downburst
    - Hazard polygons overlaid on Folium map
    - Storm arrival countdown clock for key cities
    - Automated severity summary with IMD thresholds
"""
import logging

import folium
import matplotlib.pyplot as plt
import numpy as np
import requests
import streamlit as st
from streamlit_folium import st_folium

logger = logging.getLogger(__name__)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NowCast Fusion | Convective Hazard EWS",
    page_icon="🌩️",
    layout="wide",
)

# ─── Constants ────────────────────────────────────────────────────────────────
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ASSAM_BOUNDS = [[24.0, 89.8], [28.0, 96.0]]
MAP_CENTER   = [26.0, 93.0]
MAP_ZOOM     = 6
MAP_TILE     = "CartoDB dark_matter"

SEVERITY = {
    "critical": {"label": "🔴 CRITICAL", "color": "#e74c3c", "bg": "#e74c3c22"},
    "high":     {"label": "🟠 HIGH",     "color": "#e67e22", "bg": "#e67e2222"},
    "moderate": {"label": "🟡 MODERATE", "color": "#f1c40f", "bg": "#f1c40f22"},
    "low":      {"label": "🟢 LOW",      "color": "#2ecc71", "bg": "#2ecc7122"},
}

# Auto-refresh logic (safe interval)
try:
    from streamlit_autorefresh import st_autorefresh
    # Max safe refresh for Streamlit + Folium is ~1.5 seconds. 
    # 16ms was causing the app to clear before it could render!
    auto = st.sidebar.checkbox("🟢 Auto-Refresh (Live Mode)", value=True)
    if auto:
        st_autorefresh(interval=1500, key="auto_refresh_ticker")
except ImportError:
    pass

# ─── Helper Functions ─────────────────────────────────────────────────────────

def fetch_data() -> dict | None:
    """Fetch the latest forecast from the backend (cached for 25 s)."""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/forecast/latest", timeout=20)
        if resp.status_code == 200:
            return resp.json()
        st.warning(f"Backend returned HTTP {resp.status_code}.")
    except requests.exceptions.ConnectionError:
        st.error(
            "❌ **Cannot connect to AI Backend.**  \n"
            "Run: `uvicorn src.backend.main:app --reload` in a terminal."
        )
    except Exception as exc:
        st.warning(f"Backend error: {exc}")
    return None


def colorize_rain(arr: np.ndarray, vmax: float = 20.0, threshold: float = 0.5) -> np.ndarray:
    """Convert precipitation (mm/hr) → RGBA using Jet colormap."""
    cmap  = plt.get_cmap("jet")
    rgba  = cmap(np.clip(arr / vmax, 0, 1))
    rgba[arr <  threshold, 3] = 0.0   # Transparent: no rain
    rgba[arr >= threshold, 3] = 0.65  # Semi-transparent: rainy areas
    return rgba


def colorize_hazard(arr: np.ndarray, cmap_name: str = "YlOrRd") -> np.ndarray:
    """Convert hazard probability [0–1] → RGBA."""
    cmap  = plt.get_cmap(cmap_name)
    rgba  = cmap(np.clip(arr, 0, 1))
    rgba[arr <  0.1, 3] = 0.0   # Transparent: low risk
    rgba[arr >= 0.1, 3] = 0.70  # Semi-transparent: elevated risk
    return rgba


def make_map() -> folium.Map:
    return folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM, tiles=MAP_TILE)


def add_rain_overlay(m: folium.Map, arr: np.ndarray) -> folium.Map:
    folium.raster_layers.ImageOverlay(
        image=colorize_rain(arr),
        bounds=ASSAM_BOUNDS,
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(m)
    return m


def add_hazard_overlay(m: folium.Map, arr: np.ndarray, cmap_name: str) -> folium.Map:
    folium.raster_layers.ImageOverlay(
        image=colorize_hazard(arr, cmap_name),
        bounds=ASSAM_BOUNDS,
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(m)
    return m


def add_polygons(m: folium.Map, polygons: list[dict], color: str) -> folium.Map:
    for poly in polygons:
        risk = poly.get("risk", 0)
        if risk < 0.2:
            continue
        folium.Polygon(
            locations=poly["bounds"],
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=min(0.5, risk * 0.6),
            weight=2,
            tooltip=(
                f"Risk: {risk:.0%}  |  "
                f"Centre: {poly['centroid_lat']:.2f}°N, {poly['centroid_lon']:.2f}°E"
            ),
        ).add_to(m)
    return m


def severity_badge(value: float) -> dict:
    if value > 0.75: return SEVERITY["critical"]
    if value > 0.50: return SEVERITY["high"]
    if value > 0.25: return SEVERITY["moderate"]
    return SEVERITY["low"]


def city_alert_card(cell: dict) -> None:
    eta       = cell.get("eta_minutes", "?")
    intensity = cell.get("intensity", 0)
    badge     = severity_badge(intensity / 50.0)
    st.markdown(
        f"""
        <div style="background:{badge['bg']}; border-left:4px solid {badge['color']};
                    padding:10px 14px; border-radius:6px; margin-bottom:8px;">
            <div style="font-weight:bold; font-size:1.05em;">📍 {cell['city']}</div>
            <div>🕐 ETA: <b>{eta} min</b></div>
            <div>🌧️ Intensity: <b>{intensity:.1f} mm/hr</b></div>
            <div style="font-size:0.85em; color:{badge['color']};">{badge['label']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Header ───────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title("🌩️ NowCast Fusion")
    st.markdown(
        "**Real-time Convective Hazard Early Warning System**  ·  "
        "North-East India — Assam Region  ·  "
        "Powered by **PySTEPS** optical flow + CNN enhancement"
    )
with col_refresh:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ─── Fetch Data ───────────────────────────────────────────────────────────────
with st.spinner("Fetching latest forecast from AI backend..."):
    data = fetch_data()

if not data or "error" in data:
    st.info("Waiting for backend data. Start the simulator to begin the demo.")
    st.stop()

# Parse arrays
current_map = np.array(data["current_rain_map"])
fc_30       = np.array(data["forecast_30min"])
fc_60       = np.array(data.get("forecast_60min") or data["forecast_30min"])
fc_90       = np.array(data.get("forecast_90min") or data["forecast_30min"])

hazards     = data.get("hazards", {})
cb_polys    = data.get("cloudburst_polygons", [])
lt_polys    = data.get("lightning_polygons", [])
storm_cells = data.get("storm_cells", [])


# ─── SECTION 1: Storm Arrival Countdown Clocks ────────────────────────────────
if storm_cells:
    st.subheader("⚠️ Storm Arrival Alerts")
    n_cols = min(len(storm_cells), 4)
    cols   = st.columns(n_cols)
    for i, cell in enumerate(storm_cells):
        with cols[i % n_cols]:
            city_alert_card(cell)
    st.markdown("---")


# ─── SECTION 2: Precipitation Forecast Maps ───────────────────────────────────
st.subheader("📡 Precipitation Forecast")

tab_now, tab_30, tab_60, tab_90 = st.tabs(
    ["🔵 Current", "🟡 +30 min", "🟠 +60 min", "🔴 +90 min"]
)


def rain_tab(frame: np.ndarray, key: str) -> None:
    m = add_rain_overlay(make_map(), frame)
    st_folium(m, width=720, height=460, key=key)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Peak (mm/hr)",  f"{np.max(frame):.1f}")
    col_b.metric("Mean (mm/hr)",  f"{np.mean(frame[frame > 0.5]):.1f}"
                  if np.any(frame > 0.5) else "0.0")
    col_c.metric("Coverage (%)",  f"{100 * np.mean(frame > 0.5):.1f}")


with tab_now: rain_tab(current_map, "rain_now")
with tab_30:  rain_tab(fc_30,       "rain_30")
with tab_60:  rain_tab(fc_60,       "rain_60")
with tab_90:  rain_tab(fc_90,       "rain_90")

st.markdown("---")


# ─── SECTION 3: Hazard Product Maps ──────────────────────────────────────────
st.subheader("🎯 Hazard Products  ·  (+30 min lead time)")

htab_cb, htab_hail, htab_lt, htab_db = st.tabs([
    "☁️ Cloudburst Risk",
    "🧊 Hail Probability",
    "⚡ Lightning Density",
    "💨 Downburst Risk",
])


def hazard_tab(
    hazard_key: str,
    cmap: str,
    polygons: list,
    poly_color: str,
    tab_key: str,
    description: str,
) -> None:
    if hazard_key not in hazards:
        st.info("Hazard data not yet available from the backend.")
        return

    hmap  = np.array(hazards[hazard_key])
    peak  = float(np.max(hmap))
    badge = severity_badge(peak)

    m = add_hazard_overlay(make_map(), hmap, cmap)
    add_polygons(m, polygons, poly_color)
    st_folium(m, width=720, height=460, key=tab_key)

    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.caption(description)
    with col_b:
        st.markdown(
            f'<span style="background:{badge["bg"]}; color:{badge["color"]}; '
            f'padding:4px 12px; border-radius:12px; font-weight:bold;">'
            f'{badge["label"]}  ·  {peak:.0%}</span>',
            unsafe_allow_html=True,
        )


with htab_cb:
    hazard_tab(
        "cloudburst_risk", "YlOrRd", cb_polys, "#e74c3c", "hmap_cb",
        "IMD cloudburst criterion: ≥ 100 mm in 3 hrs (≈ ≥ 50 mm/hr instantaneous rate).",
    )
with htab_hail:
    hazard_tab(
        "hail_probability", "Blues", [], "#3498db", "hmap_hail",
        "Convective intensity proxy: GPM rain rate > 25 mm/hr indicates deep cells capable of hail.",
    )
with htab_lt:
    hazard_tab(
        "lightning_density", "YlOrRd", lt_polys, "#f39c12", "hmap_lt",
        "CG lightning proxy: convective cores > 10 mm/hr correlate with strong updrafts and CG activity.",
    )
with htab_db:
    hazard_tab(
        "downburst_risk", "Purples", [], "#9b59b6", "hmap_db",
        "Microburst proxy: high precipitation intensity combined with sharp spatial gradient.",
    )

st.markdown("---")


# ─── SECTION 4: Summary Alert Panel ──────────────────────────────────────────
st.subheader("📋 Automated Hazard Summary")

max_rain = float(np.max(fc_30))
max_hail = float(np.max(hazards.get("hail_probability", [[0]])))
max_lt   = float(np.max(hazards.get("lightning_density", [[0]])))
max_db   = float(np.max(hazards.get("downburst_risk",   [[0]])))

col1, col2, col3, col4 = st.columns(4)
col1.metric("☁️ Peak Rain (+30min)", f"{max_rain:.1f} mm/hr",
            delta="CLOUDBURST" if max_rain > 50 else None,
            delta_color="inverse")
col2.metric("🧊 Hail Risk",    f"{max_hail:.0%}")
col3.metric("⚡ Lightning Index", f"{max_lt:.0%}")
col4.metric("💨 Downburst Risk",  f"{max_db:.0%}")

st.write("")

if max_rain > 50:
    st.error(
        f"🔴 **CRITICAL — CLOUDBURST RISK DETECTED**  \n"
        f"Peak forecast intensity: **{max_rain:.1f} mm/hr** exceeds the IMD cloudburst threshold.  \n"
        f"Immediate action recommended for flood-prone areas."
    )
elif max_rain > 25:
    st.warning(
        f"🟠 **HIGH ALERT — Heavy Thunderstorms + Possible Hail**  \n"
        f"Peak intensity: **{max_rain:.1f} mm/hr** · Hail risk: **{max_hail:.0%}**  \n"
        f"Prepare communities and aviation for severe convective weather."
    )
elif max_rain > 10:
    st.warning(
        f"🟡 **MODERATE ALERT — Active Convection Detected**  \n"
        f"Peak intensity: **{max_rain:.1f} mm/hr** · Lightning activity possible.  \n"
        f"Monitor situation closely."
    )
else:
    st.success(
        f"🟢 **ALL CLEAR** — No severe convective hazards predicted at this time.  \n"
        f"Peak: **{max_rain:.1f} mm/hr** · Last updated: {data.get('buffer_size', '?')} frames ingested."
    )
