"""
NowCast Fusion — FastAPI Backend

Architecture:
    - Primary forecast:  PySTEPS optical flow (Lucas-Kanade extrapolation)
    - Secondary (blend): U-Net / CNN intensity correction
    - Hazard products:   4 convective hazard maps + GeoJSON polygons
    - Data ingestion:    POST /api/v1/ingest/frame  (from simulator)
    - Forecast serving:  GET  /api/v1/forecast/latest
    - Real-time updates: WebSocket /ws/forecast
"""
import asyncio
import collections
from contextlib import asynccontextmanager
import logging
import os
from typing import Set

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Engine imports (single source of truth)
from backend.engine.nowcast_model import UNetNowcast, SimpleNowcastCNN
from backend.engine import pysteps_engine, hazard_engine, alert_engine, radar_loader, live_radar_engine
from backend.engine.openmeteo_engine import get_atmospheric_context
from backend.engine.terrain_downscale import get_or_load_srtm
from backend.engine.rendering import array_to_base64_img
from backend.settings import settings

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("nowcast.api")

# ─── In-Memory State ──────────────────────────────────────────────────────────
frame_buffer: collections.deque = collections.deque(maxlen=settings.MAX_BUFFER)
cnn_model: torch.nn.Module | None = None
srtm_data: np.ndarray | None = None
fallback_dataset: np.ndarray | None = None
MAX_VAL: float = 1.0

# WebSocket active client connections
active_websockets: Set[WebSocket] = set()


# ─── Request / Response Schemas ───────────────────────────────────────────────
class FramePayload(BaseModel):
    frame: list[list[float]]
    simulated_time: str | None = None


class RadarSweepPayload(BaseModel):
    reflectivity_dbz: list[list[float]]
    velocity_mps: list[list[float]] | None = None
    radar_site: str = "Guwahati"
    max_range_km: float = 250.0
    simulated_time: str | None = None


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cnn_model, fallback_dataset, MAX_VAL, srtm_data

    logger.info("=== NowCast Backend Starting (Lifespan) ===")

    # Load historical precipitation data (prioritize 4km PERSIANN over 10km GPM)
    data_path = settings.data_4km_path if os.path.exists(settings.data_4km_path) else settings.data_10km_path

    if os.path.exists(data_path):
        raw = np.load(data_path)  # (T, H, W) in mm/hr
        MAX_VAL = float(np.max(raw)) if np.max(raw) > 0 else 1.0
        fallback_dataset = raw
        logger.info(
            "Dataset loaded (%s): shape=%s, max=%.2f mm/hr",
            "4km PERSIANN" if "4km" in data_path else "10km GPM",
            raw.shape,
            MAX_VAL,
        )
        # Pre-seed buffer: prioritize genuine live radar sequence over historical dataset
        try:
            live_sync = live_radar_engine.sync_live_radar_into_buffer(
                frame_buffer, min_frames=settings.SEQ_IN, force_refresh=True
            )
            if len(frame_buffer) >= settings.SEQ_IN:
                logger.info("Buffer initialized with LIVE RADAR data: %s", live_sync)
        except Exception as exc:
            logger.warning("Live radar initial sync failed (%s); using fallback dataset.", exc)

        if len(frame_buffer) < settings.SEQ_IN:
            for i in range(min(settings.SEQ_IN, len(raw))):
                frame_buffer.append(raw[i])
            logger.info("Buffer pre-seeded with %d historical fallback frames.", len(frame_buffer))
    else:
        logger.warning("Data file not found at %s. Attempting live radar seed.", data_path)
        try:
            live_radar_engine.sync_live_radar_into_buffer(
                frame_buffer, min_frames=settings.SEQ_IN, force_refresh=True
            )
        except Exception as exc:
            logger.warning("Live radar seed failed: %s", exc)

    # Load trained U-Net / CNN model
    model_path = settings.MODEL_PATH
    if os.path.exists(model_path):
        try:
            # First try UNetNowcast with weights_only=True
            try:
                state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
            except Exception:
                state_dict = torch.load(model_path, map_location="cpu", weights_only=False)

            # Check architecture from state_dict keys
            if any("enc1" in k or "bottleneck" in k for k in state_dict.keys()):
                cnn_model = UNetNowcast(in_channels=settings.SEQ_IN, out_channels=settings.SEQ_IN)
                cnn_model.load_state_dict(state_dict)
                logger.info("U-Net model loaded from %s.", model_path)
            else:
                # Fallback to SimpleNowcastCNN for legacy checkpoints
                from backend.engine.nowcast_model import _DoubleConv
                # Instantiate legacy CNN if it matches old structure
                cnn_model = SimpleNowcastCNN(in_channels=settings.SEQ_IN, out_channels=settings.SEQ_IN)
                cnn_model.load_state_dict(state_dict)
                logger.info("Legacy CNN model loaded from %s.", model_path)

            cnn_model.eval()
        except Exception as exc:
            logger.warning("Model load failed: %s. Proceeding in PySTEPS-only mode.", exc)
            cnn_model = None
    else:
        logger.warning(
            "Model weights not found at %s. Run python -m backend.engine.train first. "
            "PySTEPS-only mode active.",
            model_path,
        )

    # Load SRTM terrain data for 1-km downscaling (non-blocking)
    try:
        srtm_data = get_or_load_srtm()
        logger.info("SRTM terrain data loaded: shape=%s, max=%.0f m", srtm_data.shape, srtm_data.max())
    except Exception as exc:
        logger.warning("SRTM load failed (flat maps will be used): %s", exc)
        srtm_data = None

    logger.info("=== Backend ready. ===")
    yield

    active_websockets.clear()
    logger.info("=== NowCast Backend Shutdown Complete ===")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NowCast Fusion API",
    description=(
        "Real-time convective nowcasting for North-East India (Assam Region). "
        "Primary engine: PySTEPS optical flow. Secondary: U-Net intensity correction."
    ),
    version="2.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Broadcast Helper ─────────────────────────────────────────────────────────
async def notify_websockets(message: dict) -> None:
    """Broadcast an update payload to all active WebSocket clients."""
    if not active_websockets:
        return
    disconnected = set()
    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        active_websockets.discard(ws)


# ─── Forecast Computation Function ────────────────────────────────────────────
def compute_latest_forecast() -> dict:
    """Compute the latest nowcast and hazard products from current buffer."""
    # Attempt auto-sync with latest RainViewer live radar frame
    try:
        live_radar_engine.sync_live_radar_into_buffer(frame_buffer, min_frames=settings.SEQ_IN)
    except Exception as exc:
        logger.debug("Live radar incremental sync check failed: %s", exc)

    if len(frame_buffer) < settings.SEQ_IN:
        if fallback_dataset is not None:
            seed = fallback_dataset[: settings.SEQ_IN]
            for f in seed:
                frame_buffer.append(f)
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Buffer has {len(frame_buffer)}/{settings.SEQ_IN} frames. Ingesting live radar...",
            )

    recent_frames = np.array(list(frame_buffer)[-settings.SEQ_IN :])  # (SEQ_IN, H, W)

    # ── Atmospheric Context (Open-Meteo) ──────────────────────────────────────
    atm_ctx = get_atmospheric_context()

    # ── Primary: PySTEPS Optical Flow (+6 hr, 12 steps × 30 min) ─────────────
    forecast_mm, motion_field = pysteps_engine.run_optical_flow(recent_frames, n_leadtimes=12)

    # ── Optional: U-Net / CNN Intensity Correction (blend) ───────────────────
    if cnn_model is not None:
        try:
            norm = recent_frames / MAX_VAL if MAX_VAL > 0 else recent_frames
            x_t = torch.FloatTensor(norm).unsqueeze(0)
            with torch.no_grad():
                model_output = cnn_model(x_t).squeeze(0).cpu().numpy() * MAX_VAL

            # Correctly blend overlapping lead times (e.g. first 3 lead times = +90 min)
            blend_steps = min(model_output.shape[0], forecast_mm.shape[0])
            if blend_steps > 0 and model_output.shape[1:] == forecast_mm.shape[1:]:
                alpha = settings.CNN_BLEND
                forecast_mm[:blend_steps] = (
                    (1.0 - alpha) * forecast_mm[:blend_steps] + alpha * model_output[:blend_steps]
                )
        except Exception as exc:
            logger.warning("CNN/U-Net blend skipped: %s", exc)

    current_frame = recent_frames[-1]
    forecast_30 = forecast_mm[0]
    forecast_60 = forecast_mm[1]
    forecast_90 = forecast_mm[2]
    forecast_180 = forecast_mm[5]   # +3 hours
    forecast_360 = forecast_mm[11]  # +6 hours

    # ── Hazard Products (enhanced with real CAPE + wind) ─────────────────────
    hazards = {
        "cloudburst_risk": hazard_engine.compute_cloudburst_risk(forecast_30).tolist(),
        "hail_probability": hazard_engine.compute_hail_probability(forecast_30, cape=atm_ctx["cape"]).tolist(),
        "lightning_density": hazard_engine.compute_lightning_density(forecast_30).tolist(),
        "downburst_risk": hazard_engine.compute_downburst_risk(
            forecast_30, wind_speed=atm_ctx["wind_speed"]
        ).tolist(),
    }

    cloudburst_polygons = hazard_engine.get_hazard_polygons(
        np.array(hazards["cloudburst_risk"]), threshold=0.5
    )
    lightning_polygons = hazard_engine.get_hazard_polygons(
        np.array(hazards["lightning_density"]), threshold=0.4
    )
    storm_cells = hazard_engine.get_storm_cells(forecast_mm, motion_field)

    return {
        "current_rain_map": current_frame.tolist(),
        "forecast_30min": forecast_30.tolist(),
        "forecast_60min": forecast_60.tolist(),
        "forecast_90min": forecast_90.tolist(),
        "forecast_180min": forecast_180.tolist(),
        "forecast_360min": forecast_360.tolist(),
        "images": {
            # Rain maps — terrain-enhanced 1 km resolution when SRTM available
            "current": array_to_base64_img(current_frame, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f30": array_to_base64_img(forecast_30, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f60": array_to_base64_img(forecast_60, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f90": array_to_base64_img(forecast_90, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f180": array_to_base64_img(forecast_180, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            "f360": array_to_base64_img(forecast_360, "jet", MAX_VAL, 0.5, srtm=srtm_data),
            # Hazard maps
            "cloudburst": array_to_base64_img(np.array(hazards["cloudburst_risk"]), "YlOrRd", 1.0, 0.1),
            "hail": array_to_base64_img(np.array(hazards["hail_probability"]), "Blues", 1.0, 0.1),
            "lightning": array_to_base64_img(np.array(hazards["lightning_density"]), "YlOrRd", 1.0, 0.1),
            "downburst": array_to_base64_img(np.array(hazards["downburst_risk"]), "Purples", 1.0, 0.1),
        },
        "atmospheric_context": atm_ctx,
        "hazards": hazards,
        "cloudburst_polygons": cloudburst_polygons,
        "lightning_polygons": lightning_polygons,
        "storm_cells": storm_cells,
        "alerts": alert_engine.derive_alerts(hazards, atm_ctx, storm_cells, forecast_mm),
        "buffer_size": len(frame_buffer),
        "max_val": MAX_VAL,
        "source": "live-radar" if live_radar_engine._last_ingested_timestamp > 0 else "simulator",
        "radar_timestamp": live_radar_engine._last_ingested_timestamp,
        "is_live_radar": live_radar_engine._last_ingested_timestamp > 0,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check")
def health_check() -> dict:
    return {
        "status": "ok",
        "message": "NowCast Fusion Backend v2.1 running.",
        "buffer_size": len(frame_buffer),
        "model_loaded": cnn_model is not None,
        "srtm_loaded": srtm_data is not None,
        "ws_connections": len(active_websockets),
    }


@app.post(
    "/api/v1/ingest/frame",
    tags=["Ingest"],
    summary="Push a precipitation frame from the data simulator",
)
async def ingest_frame(payload: FramePayload) -> dict:
    """
    Accept a single precipitation frame (mm/hr) from the data simulator and
    append it to the in-memory sliding window buffer used for nowcasting.
    Broadcasts a notification to connected WebSocket clients.
    """
    try:
        frame = np.array(payload.frame, dtype=float)
        if frame.ndim != 2:
            raise ValueError(f"Expected 2-D frame, got shape {frame.shape}")

        frame_buffer.append(frame)
        logger.info(
            "Frame ingested | sim_time=%s | shape=%s | max=%.2f mm/hr | buffer=%d",
            payload.simulated_time,
            frame.shape,
            np.max(frame),
            len(frame_buffer),
        )

        # Notify WebSockets about new data arrival
        asyncio.create_task(
            notify_websockets({
                "type": "frame_ingested",
                "simulated_time": payload.simulated_time,
                "buffer_size": len(frame_buffer),
            })
        )

        return {"status": "ok", "buffer_size": len(frame_buffer)}

    except Exception as exc:
        logger.error("Frame ingestion failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/v1/ingest/radar-sweep",
    tags=["Ingest"],
    summary="Ingest a Doppler Weather Radar polar sweep (dBZ + velocity)",
)
async def ingest_radar_sweep(payload: RadarSweepPayload) -> dict:
    """
    Ingest raw Doppler Weather Radar sweep data (polar PPI: azimuth x range).
    Converts reflectivity (dBZ) to precipitation (mm/hr) via Marshall-Palmer (Z = 200 R^1.6),
    rasterizes the polar coordinates to the Cartesian regional domain, and analyzes
    radial velocity shear for microburst detection.
    """
    try:
        dbz_sweep = np.array(payload.reflectivity_dbz, dtype=float)
        if dbz_sweep.ndim != 2:
            raise ValueError(f"Expected 2-D polar sweep (azimuth x range), got shape {dbz_sweep.shape}")

        site_info = radar_loader.IMD_DWR_SITES.get(
            payload.radar_site,
            radar_loader.IMD_DWR_SITES["Guwahati"],
        )

        # 1. Convert dBZ -> mm/hr
        rain_polar = radar_loader.dbz_to_rain_rate(dbz_sweep)

        # 2. Target grid shape (match current buffer or standard 100x155)
        grid_shape = (100, 155)
        if len(frame_buffer) > 0:
            grid_shape = frame_buffer[-1].shape

        cartesian_rain = radar_loader.polar_to_cartesian_grid(
            polar_sweep=rain_polar,
            radar_lat=site_info["lat"],
            radar_lon=site_info["lon"],
            max_range_km=payload.max_range_km,
            grid_shape=grid_shape,
        )

        # 3. Optional radial velocity analysis
        shear_info = None
        if payload.velocity_mps is not None:
            vel_sweep = np.array(payload.velocity_mps, dtype=float)
            shear_info = radar_loader.compute_radial_shear(vel_sweep)

        frame_buffer.append(cartesian_rain)
        logger.info(
            "Radar sweep ingested | site=%s | max_dBZ=%.1f | peak_rain=%.2f mm/hr | buffer=%d",
            payload.radar_site,
            float(np.max(dbz_sweep)),
            float(np.max(cartesian_rain)),
            len(frame_buffer),
        )

        asyncio.create_task(
            notify_websockets({
                "type": "frame_ingested",
                "source": "dwr",
                "site": payload.radar_site,
                "simulated_time": payload.simulated_time,
                "buffer_size": len(frame_buffer),
            })
        )

        return {
            "status": "ok",
            "radar_site": payload.radar_site,
            "max_rain_mm_hr": round(float(np.max(cartesian_rain)), 2),
            "buffer_size": len(frame_buffer),
            "shear_info": shear_info,
        }

    except Exception as exc:
        logger.error("Radar sweep ingestion failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/v1/ingest/sync-live-radar",
    tags=["Ingest"],
    summary="Synchronize live radar from RainViewer and recompute nowcast",
)
async def sync_live_radar_endpoint() -> dict:
    """
    Fetch the latest live Doppler radar sweeps from RainViewer covering Assam,
    update the frame buffer with live observations, and broadcast the recomputed forecast.
    """
    try:
        sync_res = live_radar_engine.sync_live_radar_into_buffer(
            frame_buffer, min_frames=settings.SEQ_IN, force_refresh=True
        )
        forecast = compute_latest_forecast()
        asyncio.create_task(notify_websockets({"type": "forecast", "data": forecast}))
        return {"status": "ok", "sync": sync_res, "forecast": forecast}
    except Exception as exc:
        logger.error("Live radar sync failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Live radar sync failed: {exc}") from exc


@app.get(
    "/api/v1/forecast/latest",
    tags=["Forecast"],
    summary="Get the latest nowcast + all 4 hazard products",
)
def get_forecast() -> dict:
    return compute_latest_forecast()


@app.websocket("/ws/forecast")
async def websocket_forecast(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for instant forecast updates.
    Sends the latest forecast upon connection and accepts 'refresh' pings.
    """
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        # Send initial forecast upon connection
        try:
            fc = compute_latest_forecast()
            await websocket.send_json({"type": "forecast", "data": fc})
        except Exception as e:
            await websocket.send_json({"type": "error", "detail": str(e)})

        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
            elif msg == "get_forecast":
                fc = compute_latest_forecast()
                await websocket.send_json({"type": "forecast", "data": fc})
    except WebSocketDisconnect:
        active_websockets.discard(websocket)
    except Exception as exc:
        logger.debug("WebSocket exception: %s", exc)
        active_websockets.discard(websocket)
