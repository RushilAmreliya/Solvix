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
from src.engine.nowcast_model import SimpleNowcastCNN
from src.engine import pysteps_engine, hazard_engine

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
fallback_dataset: np.ndarray | None = None   # Used when buffer is empty
MAX_VAL   = 1.0


# ─── Request / Response Schemas ───────────────────────────────────────────────
class FramePayload(BaseModel):
    frame: list[list[float]]
    simulated_time: str | None = None


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def load_assets() -> None:
    global cnn_model, fallback_dataset, MAX_VAL

    logger.info("=== NowCast Backend Starting ===")

    # Load historical GPM data as fallback seed
    data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/assam_gpm_sample.npy")
    )
    if os.path.exists(data_path):
        raw      = np.load(data_path)           # (T, H, W) in mm/hr
        MAX_VAL  = float(np.max(raw)) if np.max(raw) > 0 else 1.0
        fallback_dataset = raw
        logger.info(
            "Dataset loaded: shape=%s, max=%.2f mm/hr", raw.shape, MAX_VAL
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


# ─── Base64 Image Helper ──────────────────────────────────────────────────────
import io
import base64
from PIL import Image
import matplotlib.pyplot as plt
import cv2

def array_to_base64_img(arr: np.ndarray, cmap_name: str = "jet", vmax: float = 20.0, threshold: float = 0.5) -> str:
    """Convert a 2D precipitation or hazard array to a smooth transparent PNG base64 string."""
    # Smooth the pixelated grid using bicubic interpolation (10x higher resolution) + Gaussian blur
    h, w = arr.shape
    smooth_arr = cv2.resize(arr, (w * 10, h * 10), interpolation=cv2.INTER_CUBIC)
    smooth_arr = np.clip(smooth_arr, 0, None)
    # Gentle gaussian blur to produce smooth convective radar contours
    smooth_arr = cv2.GaussianBlur(smooth_arr, (11, 11), 0)
    
    normed = np.clip(smooth_arr / vmax, 0, 1)
    cmap = plt.get_cmap(cmap_name)
    rgba = cmap(normed)
    rgba[smooth_arr < threshold, 3] = 0.0
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
    """
    Run the nowcasting pipeline on the most recent buffered frames and return:

    - `current_rain_map`     — most recent observed precipitation (mm/hr)
    - `forecast_30min`       — +30 min forecast  (mm/hr)
    - `forecast_60min`       — +60 min forecast  (mm/hr)
    - `forecast_90min`       — +90 min forecast  (mm/hr)
    - `hazards`              — dict of 4 hazard probability maps [0–1]
    - `cloudburst_polygons`  — GeoJSON-ready polygons for severe cloudburst zones
    - `lightning_polygons`   — GeoJSON-ready polygons for lightning risk zones
    - `storm_cells`          — list of city ETAs where storm arrival is imminent
    - `buffer_size`          — number of frames currently in the buffer
    """
    # ── Ensure we have enough frames ─────────────────────────────────────────
    if len(frame_buffer) < SEQ_IN:
        if fallback_dataset is not None:
            logger.warning(
                "Buffer has only %d frames (need %d). Using fallback dataset seed.",
                len(frame_buffer), SEQ_IN,
            )
            seed = fallback_dataset[:SEQ_IN]
            for f in seed:
                frame_buffer.append(f)
        else:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Frame buffer has {len(frame_buffer)}/{SEQ_IN} frames. "
                    "Start the data simulator or wait for frames to arrive."
                ),
            )

    recent_frames = np.array(list(frame_buffer)[-SEQ_IN:])   # (SEQ_IN, H, W) mm/hr

    # ── Primary: PySTEPS Optical Flow Extrapolation ───────────────────────────
    forecast_mm, motion_field = pysteps_engine.run_optical_flow(
        recent_frames, n_leadtimes=3
    )

    # ── Optional: CNN Intensity Correction (blend 70% PySTEPS + 30% CNN) ─────
    if cnn_model is not None:
        try:
            norm = recent_frames / MAX_VAL if MAX_VAL > 0 else recent_frames
            with torch.no_grad():
                x_t    = torch.FloatTensor(norm).unsqueeze(0)
                cnn_fc = cnn_model(x_t).squeeze(0).numpy() * MAX_VAL

            # Ensure CNN output matches PySTEPS shape (may differ if sizes change)
            if cnn_fc.shape == forecast_mm.shape:
                forecast_mm = 0.70 * forecast_mm + 0.30 * cnn_fc
                logger.info("CNN enhancement applied (70/30 blend).")
            else:
                logger.warning(
                    "CNN output shape %s != PySTEPS shape %s. Skipping blend.",
                    cnn_fc.shape, forecast_mm.shape,
                )
        except Exception as exc:
            logger.warning("CNN blend skipped: %s", exc)

    current_frame = recent_frames[-1]            # Most recent observed frame
    forecast_30   = forecast_mm[0]               # +30 min
    forecast_60   = forecast_mm[1] if len(forecast_mm) > 1 else forecast_30
    forecast_90   = forecast_mm[2] if len(forecast_mm) > 2 else forecast_30

    # ── Hazard Products ───────────────────────────────────────────────────────
    hazards = {
        "cloudburst_risk":   hazard_engine.compute_cloudburst_risk(forecast_30).tolist(),
        "hail_probability":  hazard_engine.compute_hail_probability(forecast_30).tolist(),
        "lightning_density": hazard_engine.compute_lightning_density(forecast_30).tolist(),
        "downburst_risk":    hazard_engine.compute_downburst_risk(forecast_30).tolist(),
    }

    # ── Hazard Polygons ───────────────────────────────────────────────────────
    cloudburst_polygons = hazard_engine.get_hazard_polygons(
        np.array(hazards["cloudburst_risk"]),  threshold=0.5
    )
    lightning_polygons = hazard_engine.get_hazard_polygons(
        np.array(hazards["lightning_density"]), threshold=0.4
    )

    # ── Storm Cell ETA ────────────────────────────────────────────────────────
    storm_cells = hazard_engine.get_storm_cells(forecast_mm, motion_field)

    return {
        "current_rain_map":      current_frame.tolist(),
        "forecast_30min":        forecast_30.tolist(),
        "forecast_60min":        forecast_60.tolist(),
        "forecast_90min":        forecast_90.tolist(),
        
        "images": {
            "current": array_to_base64_img(current_frame, "jet", 20.0, 0.5),
            "f30": array_to_base64_img(forecast_30, "jet", 20.0, 0.5),
            "f60": array_to_base64_img(forecast_60, "jet", 20.0, 0.5),
            "f90": array_to_base64_img(forecast_90, "jet", 20.0, 0.5),
            
            "cloudburst": array_to_base64_img(np.array(hazards["cloudburst_risk"]), "YlOrRd", 1.0, 0.1),
            "hail": array_to_base64_img(np.array(hazards["hail_probability"]), "Blues", 1.0, 0.1),
            "lightning": array_to_base64_img(np.array(hazards["lightning_density"]), "YlOrRd", 1.0, 0.1),
            "downburst": array_to_base64_img(np.array(hazards["downburst_risk"]), "Purples", 1.0, 0.1)
        },
        
        "hazards":               hazards,
        "cloudburst_polygons":   cloudburst_polygons,
        "lightning_polygons":    lightning_polygons,
        "storm_cells":           storm_cells,
        "buffer_size":           len(frame_buffer),
    }
