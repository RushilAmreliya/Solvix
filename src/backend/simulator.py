"""
NowCast Fusion — Historical Data Simulator

Replays a historical severe weather event (Assam squall line, May 2023)
chronologically, POSTing each precipitation frame to the FastAPI backend
as if it were a live data feed.

Usage:
    # Normal speed (10x faster than real-time for demo):
    python -m src.backend.simulator --speed 0.1 --loop

    # Ultra-fast (fill the buffer instantly):
    python -m src.backend.simulator --speed 0.001 --loop

    # Custom backend URL (e.g. deployed on Render):
    python -m src.backend.simulator --backend https://nowcast-backend-fjl8.onrender.com
"""
import argparse
import logging
import time
from datetime import datetime, timedelta

import numpy as np
import requests

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIMULATOR] %(message)s",
)
logger = logging.getLogger("nowcast.simulator")

# ─── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_BACKEND  = "http://localhost:8000"
DEFAULT_DATA     = "data/assam_persiann_4km.npy" if os.path.exists("data/assam_persiann_4km.npy") else "data/assam_gpm_sample.npy"
DEFAULT_INTERVAL = 30       # Simulated minutes between frames
DEFAULT_SPEED    = 0.001    # 0.001 = each frame is sent every (30*60*0.001) = 1.8 seconds


def run_simulator(
    backend_url: str,
    data_path:   str,
    interval_minutes: int,
    fps:         float,
    loop:        bool,
) -> None:
    """
    Load the historical data cube and stream frames to the NowCast backend.

    Args:
        backend_url:      Base URL of the FastAPI backend
        data_path:        Path to the (T, H, W) .npy precipitation array in mm/hr
        interval_minutes: Simulated time gap between consecutive frames
        fps:              Frames per second to transmit (60.0 = fast playback)
        loop:             Whether to restart from the beginning after finishing
    """
    logger.info("Loading data from '%s'...", data_path)
    try:
        data = np.load(data_path)
    except FileNotFoundError:
        logger.error(
            "Data file not found: %s\n"
            "Run 'python -m src.engine.fetch_gee_data' first.",
            data_path,
        )
        return

    T, H, W = data.shape
    real_wait_s  = 1.0 / fps if fps > 0 else 1.0
    
    logger.info(
        "Dataset loaded: %d frames of %d×%d pixels | max: %.2f mm/hr",
        T, H, W, np.max(data),
    )
    logger.info(
        "Streaming to %s at %.1f FPS (%.3f sec / frame).",
        backend_url, fps, real_wait_s,
    )

    ingest_url   = f"{backend_url}/api/v1/ingest/frame"

    # Verify backend is reachable before starting
    try:
        health = requests.get(f"{backend_url}/", timeout=5)
        logger.info("Backend status: %s", health.json().get("message", "ok"))
    except Exception as exc:
        logger.error(
            "Cannot reach backend at %s: %s\n"
            "Start the backend first with: uvicorn src.backend.main:app --reload",
            backend_url, exc,
        )
        return

    sim_time = datetime(2023, 5, 15, 12, 0, 0)   # Historical event start

    while True:
        logger.info("─── Starting replay of %d frames ───", T)

        for t in range(T):
            frame   = data[t]                            # (H, W) mm/hr
            ts_str  = sim_time.strftime("%Y-%m-%d %H:%M")

            payload = {
                "frame":          frame.tolist(),
                "simulated_time": ts_str,
            }

            try:
                resp = requests.post(ingest_url, json=payload, timeout=15)

                if resp.status_code == 200:
                    buf_size = resp.json().get("buffer_size", "?")
                    logger.info(
                        "[%03d/%03d] t=%s | max=%.1f mm/hr | buffer=%s",
                        t + 1, T, ts_str, np.max(frame), buf_size,
                    )
                else:
                    logger.warning(
                        "[%03d/%03d] Backend returned HTTP %d: %s",
                        t + 1, T, resp.status_code, resp.text[:200],
                    )

            except requests.exceptions.ConnectionError:
                logger.error(
                    "Connection lost to %s. Retrying next frame...", backend_url
                )
            except requests.exceptions.Timeout:
                logger.warning("Request timed out for frame %d. Skipping.", t + 1)
            except Exception as exc:
                logger.error("Unexpected error on frame %d: %s", t + 1, exc)

            sim_time += timedelta(minutes=interval_minutes)
            time.sleep(real_wait_s)

        if loop:
            logger.info("Replay complete. Looping back to start (sim_time reset).")
            sim_time = datetime(2023, 5, 15, 12, 0, 0)
        else:
            logger.info("Replay complete. Use --loop to replay continuously.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NowCast Fusion — Historical Data Simulator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--backend",  default=DEFAULT_BACKEND,
                        help="Base URL of the FastAPI backend")
    parser.add_argument("--data",     default=DEFAULT_DATA,
                        help="Path to the .npy data cube (T, H, W) in mm/hr")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="Simulated minutes between consecutive frames")
    parser.add_argument("--fps",      type=float, default=60.0,
                        help="Target frames per second for playback (e.g. 60.0)")
    parser.add_argument("--loop",     action="store_true",
                        help="Loop the dataset continuously after finishing")
    args = parser.parse_args()

    try:
        run_simulator(args.backend, args.data, args.interval, args.fps, args.loop)
    except KeyboardInterrupt:
        logger.info("Simulator stopped by user.")


if __name__ == "__main__":
    main()
