"""
NASA Earthdata GPM IMERG Downloader
Credentials are read from _netrc — NEVER stored in code.

Setup:
    python setup_credentials.py    ← run this once first

Usage:
    python -m src.engine.fetch_earthdata
    python -m src.engine.fetch_earthdata --start 2023-06-01 --end 2023-08-31
"""
import os
import sys
import logging
import argparse
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

BBOX       = [89.8, 24.0, 96.0, 28.0]     # [W, S, E, N]
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))


def download_gpm_imerg(
    start_date:  str = "2023-06-01",
    end_date:    str = "2023-08-31",
    output_path: str | None = None,
) -> str:
    """
    Download GPM IMERG Half-Hourly data from NASA Earthdata.

    Credentials are automatically read from ~/.netrc / ~/_netrc.
    Never pass credentials as arguments — use setup_credentials.py.

    Args:
        start_date:  ISO date string (YYYY-MM-DD)
        end_date:    ISO date string (YYYY-MM-DD)
        output_path: Where to save the resulting .npy file

    Returns:
        Absolute path to the saved .npy file
    """
    try:
        import earthaccess
    except ImportError:
        logger.error("earthaccess is not installed. Run: pip install earthaccess")
        sys.exit(1)

    # Auto-derive output filename
    if output_path is None:
        days   = (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days
        months = max(1, days // 28)
        output_path = os.path.join(OUTPUT_DIR, f"assam_gpm_{months}mo.npy")

    # ── Authenticate from netrc ──────────────────────────────────────────────
    logger.info("Authenticating with NASA Earthdata (reading from _netrc)…")
    try:
        earthaccess.login(strategy="netrc")
        logger.info("Authentication successful.")
    except Exception as exc:
        logger.error(
            "Authentication failed: %s\n"
            "Run: python setup_credentials.py  to set up your NASA Earthdata credentials.",
            exc,
        )
        sys.exit(1)

    # ── Search ───────────────────────────────────────────────────────────────
    logger.info("Searching GPM IMERG (%s → %s) over bbox %s…", start_date, end_date, BBOX)
    try:
        results = earthaccess.search_data(
            short_name="GPM_3IMERGHH",          # GPM IMERG Half-Hourly V07
            temporal=(start_date, end_date),
            bounding_box=tuple(BBOX),
        )
    except Exception as exc:
        logger.error("Search failed: %s", exc)
        sys.exit(1)

    logger.info("Found %d granules.", len(results))
    if not results:
        logger.error("No data found for the requested period.")
        sys.exit(1)

    # ── Download ─────────────────────────────────────────────────────────────
    import tempfile
    import h5py

    frames = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger.info("Downloading %d granules to temp dir…", len(results))
        try:
            files = earthaccess.download(results, local_path=tmp_dir)
        except Exception as exc:
            logger.error("Download failed: %s", exc)
            sys.exit(1)

        logger.info("Extracting precipitationCal from %d files…", len(files))
        for fpath in sorted(files):
            try:
                with h5py.File(fpath, "r") as f:
                    precip = f["Grid/precipitationCal"][0]            # (lat, lon)
                    precip = np.where(precip < 0, 0.0, precip).astype(np.float32)
                    frames.append(precip)
            except Exception as exc:
                logger.warning("Skipping %s: %s", os.path.basename(fpath), exc)

    if not frames:
        logger.error("No frames could be extracted.")
        sys.exit(1)

    # ── Save ─────────────────────────────────────────────────────────────────
    data = np.stack(frames, axis=0)     # (T, H, W)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    np.save(output_path, data)

    size_mb = os.path.getsize(output_path) / 1e6
    logger.info(
        "Saved %d frames, shape=%s, max=%.2f mm/hr → %s (%.1f MB)",
        len(frames), data.shape, data.max(), output_path, size_mb,
    )
    return output_path


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="Download GPM IMERG data from NASA Earthdata")
    parser.add_argument("--start",  default="2023-06-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end",    default="2023-08-31", help="End date YYYY-MM-DD")
    parser.add_argument("--output", default=None,         help="Output .npy file path")
    args = parser.parse_args()

    path = download_gpm_imerg(args.start, args.end, args.output)
    print(f"\n✅  Data saved to: {path}")
