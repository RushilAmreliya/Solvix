"""
NowCast Fusion — FastAPI Backend

Architecture:
    - Primary forecast:  PySTEPS optical flow (Lucas-Kanade extrapolation)
    - Secondary (blend): Lightweight CNN for intensity correction
    - Hazard products:   4 convective hazard maps + GeoJSON polygons
    - Data ingestion:    POST /api/v1/ingest/frame  (from simulator)
    - Forecast serving:  GET  /api/v1/forecast/latest
"""
import collections
import logging
import os

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Engine imports (single source of truth)
from src.engine.nowcast_model        import SimpleNowcastCNN
from src.engine                      import pysteps_engine, hazard_engine
from src.engine.openmeteo_engine     import get_atmospheric_context
from src.engine.terrain_downscale    import get_or_load_srtm, downscale_to_1km

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("nowcast.api")

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NowCast Fusion API",
    description=(
        "Real-time convective nowcasting for North-East India (Assam Region). "
        "Primary engine: PySTEPS optical flow. Secondary: CNN intensity correction."
    ),
    version="2.0.0",
)

# CORS — open for SIH demo prototype; restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-Memory State ──────────────────────────────────────────────────────────
SEQ_IN      = 3         # Frames fed to PySTEPS / CNN  (3 × 30 min = 1.5 hrs)
MAX_BUFFER  = 20        # Maximum frames held in memory

# Sliding window of recent frames (mm/hr, raw)
frame_buffer: collections.deque = collections.deque(maxlen=MAX_BUFFER)

cnn_model = None
srtm_data: np.ndarray | None = None   # SRTM terrain elevation grid for 1-km downscaling
fallback_dataset: np.ndarray | None = None   # Used when buffer is empty
MAX_VAL   = 1.0


# ─── Request / Response Schemas ───────────────────────────────────────────────
class FramePayload(BaseModel):
    frame: list[list[float]]
    simulated_time: str | None = None


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def load_assets() -> None:
    global cnn_model, fallback_dataset, MAX_VAL, srtm_data

    logger.info("=== NowCast Backend Starting ===")

    # Load historical precipitation data (prioritize 4km PERSIANN over 10km GPM)
    data_4km = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/assam_persiann_4km.npy")
    )
    data_10km = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/assam_gpm_sample.npy")
    )
    data_path = data_4km if os.path.exists(data_4km) else data_10km

    if os.path.exists(data_path):
        raw      = np.load(data_path)           # (T, H, W) in mm/hr
        MAX_VAL  = float(np.max(raw)) if np.max(raw) > 0 else 1.0
        fallback_dataset = raw
        logger.info(
            "Dataset loaded (%s): shape=%s, max=%.2f mm/hr",
            "4km PERSIANN" if "4km" in data_path else "10km GPM",
            raw.shape, MAX_VAL
        )
        # Pre-seed buffer with initial frames so the first API call works
        for i in range(min(SEQ_IN, len(raw))):
            frame_buffer.append(raw[i])
        logger.info("Buffer pre-seeded with %d frames.", len(frame_buffer))
    else:
        logger.warning("Data file not found at %s. Start simulator to fill buffer.", data_path)

    # Load trained CNN model (optional enhancement)
    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../engine/nowcast_model.pth")
    )
    if os.path.exists(model_path):
        cnn_model = SimpleNowcastCNN(in_channels=SEQ_IN, out_channels=SEQ_IN)
        cnn_model.load_state_dict(torch.load(model_path, map_location="cpu"))
        cnn_model.eval()
        logger.info("CNN model loaded from %s.", model_path)
    else:
        logger.warning(
            "CNN model not found at %s. Run src/engine/train.py first. "
            "PySTEPS-only mode active.", model_path
        )

    logger.info("=== Backend ready. ===")

    # Load SRTM terrain data for 1-km downscaling (non-blocking — uses cache if available)
    try:
        srtm_data = get_or_load_srtm()
        logger.info("SRTM terrain data loaded: shape=%s, max=%.0f m", srtm_data.shape, srtm_data.max())
    except Exception as exc:
        logger.warning("SRTM load failed (flat maps will be used): %s", exc)
        srtm_data = None


# ─── Base64 Image Helper ──────────────────────────────────────────────────────
import io
import base64
from PIL import Image
import matplotlib.pyplot as plt
import cv2

def array_to_base64_img(
    arr: np.ndarray,
    cmap_name: str = "jet",
    vmax: float = 20.0,
    threshold: float = 0.5,
    srtm: np.ndarray | None = None,
) -> str:
    """Convert a 2D precipitation or hazard array to a smooth transparent PNG base64 string."""
    # Optional: terrain downscaling to ~1 km before smoothing
    if srtm is not None:
        arr = downscale_to_1km(arr, srtm)
        # Already upscaled — skip the 10x resize below, just do light smoothing
        smooth_arr = np.clip(arr, 0, None).astype(np.float32)
        smooth_arr = cv2.GaussianBlur(smooth_arr, (11, 11), 0)
    else:
        # Standard 10x bicubic upsample + blur
        h, w = arr.shape
        smooth_arr = cv2.resize(arr.astype(np.float32), (w * 10, h * 10), interpolation=cv2.INTER_CUBIC)
        smooth_arr = np.clip(smooth_arr, 0, None)
        smooth_arr = cv2.GaussianBlur(smooth_arr, (11, 11), 0)

    normed = np.clip(smooth_arr / vmax, 0, 1)
    cmap   = plt.get_cmap(cmap_name)
    rgba   = cmap(normed)
    rgba[smooth_arr <  threshold, 3] = 0.0
    rgba[smooth_arr >= threshold, 3] = 0.70
    img = Image.fromarray((rgba * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="Health check")
def health_check() -> dict:
    return {
        "status":       "ok",
        "message":      "NowCast Fusion Backend v2.0 running.",
        "buffer_size":  len(frame_buffer),
        "cnn_loaded":   cnn_model is not None,
        "srtm_loaded":  srtm_data is not None,
    }


@app.post(
    "/api/v1/ingest/frame",
    tags=["Ingest"],
    summary="Push a precipitation frame from the data simulator",
)
def ingest_frame(payload: FramePayload) -> dict:
    """
    Accept a single precipitation frame (mm/hr) from the data simulator and
    append it to the in-memory sliding window buffer used for nowcasting.
    """
    try:
        frame = np.array(payload.frame, dtype=float)
        if frame.ndim != 2:
            raise ValueError(f"Expected 2-D frame, got shape {frame.shape}")

        frame_buffer.append(frame)
        logger.info(
            "Frame ingested | sim_time=%s | shape=%s | max=%.2f mm/hr | buffer=%d",
            payload.simulated_time, frame.shape, np.max(frame), len(frame_buffer),
        )
        return {"status": "ok", "buffer_size": len(frame_buffer)}

    except Exception as exc:
        logger.error("Frame ingestion failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/v1/forecast/latest",
    tags=["Forecast"],
    summary="Get the latest nowcast + all 4 hazard products",
)
def get_forecast() -> dict:
    # ── Ensure we have enough frames ─────────────────────────────────────────
    if len(frame_buffer) < SEQ_IN:
        if fallback_dataset is not None:
            seed = fallback_dataset[:SEQ_IN]
            for f in seed:
                frame_buffer.append(f)
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Buffer has {len(frame_buffer)}/{SEQ_IN} frames. Start the simulator.",
            )

    recent_frames = np.array(list(frame_buffer)[-SEQ_IN:])   # (SEQ_IN, H, W)

    # ── Atmospheric Context (Open-Meteo) ──────────────────────────────────────
    atm_ctx = get_atmospheric_context()

    # ── Primary: PySTEPS Optical Flow (+6 hr, 12 steps × 30 min) ─────────────
    forecast_mm, motion_field = pysteps_engine.run_optical_flow(
        recent_frames, n_leadtimes=12
    )

    # ── Optional: CNN Intensity Correction (70/30 blend) ─────────────────────
    if cnn_model is not None:
        try:
            norm   = recent_frames / MAX_VAL if MAX_VAL > 0 else recent_frames
            x_t    = torch.FloatTensor(norm).unsqueeze(0)
            with torch.no_grad():
                cnn_fc = cnn_model(x_t).squeeze(0).numpy() * MAX_VAL
            if cnn_fc.shape == forecast_mm.shape:
                forecast_mm = 0.70 * forecast_mm + 0.30 * cnn_fc
        except Exception as exc:
            logger.warning("CNN blend skipped: %s", exc)

    current_frame = recent_frames[-1]
    forecast_30   = forecast_mm[0]
    forecast_60   = forecast_mm[1]
    forecast_90   = forecast_mm[2]
    forecast_180  = forecast_mm[5]    # +3 hours
    forecast_360  = forecast_mm[11]   # +6 hours

    # ── Hazard Products (enhanced with real CAPE + wind) ─────────────────────
    hazards = {
        "cloudburst_risk":   hazard_engine.compute_cloudburst_risk(forecast_30).tolist(),
        "hail_probability":  hazard_engine.compute_hail_probability(
                                 forecast_30, cape=atm_ctx["cape"]).tolist(),
        "lightning_density": hazard_engine.compute_lightning_density(forecast_30).tolist(),
        "downburst_risk":    hazard_engine.compute_downburst_risk(
                                 forecast_30, wind_speed=atm_ctx["wind_speed"]).tolist(),
    }

    cloudburst_polygons = hazard_engine.get_hazard_polygons(
        np.array(hazards["cloudburst_risk"]),  threshold=0.5
    )
    lightning_polygons = hazard_engine.get_hazard_polygons(
        np.array(hazards["lightning_density"]), threshold=0.4
    )
    storm_cells = hazard_engine.get_storm_cells(forecast_mm, motion_field)

    # ── Build Response ────────────────────────────────────────────────────────
    return {
        "current_rain_map": current_frame.tolist(),
        "forecast_30min":   forecast_30.tolist(),
        "forecast_60min":   forecast_60.tolist(),
        "forecast_90min":   forecast_90.tolist(),
        "forecast_180min":  forecast_180.tolist(),
        "forecast_360min":  forecast_360.tolist(),

        "images": {
            # Rain maps — terrain-enhanced 1 km resolution when SRTM available
            "current": array_to_base64_img(current_frame, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f30":     array_to_base64_img(forecast_30,   "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f60":     array_to_base64_img(forecast_60,   "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f90":     array_to_base64_img(forecast_90,   "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f180":    array_to_base64_img(forecast_180,  "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f360":    array_to_base64_img(forecast_360,  "jet", MAX_VAL, 0.5, srtm=srtm_data),
            # Hazard maps (no terrain scaling — probability fields)
            "cloudburst": array_to_base64_img(np.array(hazards["cloudburst_risk"]),  "YlOrRd", 1.0, 0.1),
            "hail":       array_to_base64_img(np.array(hazards["hail_probability"]), "Blues",  1.0, 0.1),
            "lightning":  array_to_base64_img(np.array(hazards["lightning_density"]),"YlOrRd", 1.0, 0.1),
            "downburst":  array_to_base64_img(np.array(hazards["downburst_risk"]),   "Purples",1.0, 0.1),
        },

        "atmospheric_context": atm_ctx,
        "hazards":             hazards,
        "cloudburst_polygons": cloudburst_polygons,
        "lightning_polygons":  lightning_polygons,
        "storm_cells":         storm_cells,
        "buffer_size":         len(frame_buffer),
    }
