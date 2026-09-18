"""
PERSIANN-CCS 4km Resolution Satellite Precipitation Fetcher
Downloads and crops hourly 4km precipitation data for North-East India / Assam.

Data Provider:
    Center for Hydrometeorology and Remote Sensing (CHRS), UC Irvine.
    Coverage: 60°S - 60°N, 0° - 360°
    Resolution: 0.04° x 0.04° (~4km)
    Grid: 3000 rows x 9000 cols
    Assam Crop: Rows 800:900 (28°N to 24°N), Cols 2245:2400 (89.8°E to 96.0°E)
    Result shape per frame: (100, 155) -> 15,500 grid cells!
"""
import os
import sys
import ftplib
import gzip
import io
import logging
import argparse
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

# CHRS FTP Server IP (bypasses DNS resolution issues)
CHRS_FTP_HOST = "128.200.89.195"
FTP_BASE_DIR  = "CHRSdata/PERSIANN-CCS/hrly"

# Assam 4km grid coordinates
# Rows 800:900 correspond to 28°N down to 24°N
# Cols 2245:2400 correspond to 89.8°E to 96.0°E
ROW_START, ROW_END = 800, 900
COL_START, COL_END = 2245, 2400
TARGET_H, TARGET_W = 100, 155

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))


def download_persiann_frames(year: int = 2023, max_frames: int = 168, output_path: str = None) -> str:
    """
    Download hourly 4km PERSIANN-CCS frames from CHRS FTP,
    crop to Assam bounding box (100x155), and save as a 3D NumPy array.
    
    Default max_frames=168 is 1 full week (7 days x 24 hrs = 168 frames).
    """
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"assam_persiann_4km_{year}.npy")

    logger.info("Connecting to CHRS FTP (%s)...", CHRS_FTP_HOST)
    ftp = ftplib.FTP(CHRS_FTP_HOST, timeout=30)
    ftp.login()
    ftp.set_pasv(True)

    ftp_path = f"{FTP_BASE_DIR}/{year}"
    ftp.cwd(ftp_path)
    
    all_files = sorted([f for f in ftp.nlst() if f.endswith(".bin.gz")])
    logger.info("Found %d hourly files for year %d.", len(all_files), year)
    
    if not all_files:
        ftp.quit()
        raise ValueError(f"No files found in {ftp_path}")

    selected_files = all_files[:max_frames]
    logger.info("Downloading and processing %d frames (4km resolution)...", len(selected_files))

    frames = []
    for i, fname in enumerate(selected_files):
        buf = io.BytesIO()
        try:
            ftp.retrbinary(f"RETR {fname}", buf.write)
            buf.seek(0)
            with gzip.GzipFile(fileobj=buf) as gz:
                raw = gz.read()

            # Global grid: 3000 x 9000 int16 big-endian, values are mm/hr * 100
            grid = np.frombuffer(raw, dtype=">i2").reshape((3000, 9000))
            precip = grid.astype(np.float32) / 100.0

            # Crop Assam bounding box (100 rows x 155 cols)
            assam_crop = precip[ROW_START:ROW_END, COL_START:COL_END]
            assam_crop = np.where(assam_crop < 0, 0.0, assam_crop)
            frames.append(assam_crop)

            if (i + 1) % 10 == 0 or (i + 1) == len(selected_files):
                logger.info("Processed %d/%d frames (Current max: %.2f mm/hr)", i + 1, len(selected_files), assam_crop.max())
        except Exception as e:
            logger.warning("Error processing %s: %s", fname, e)
            continue

    ftp.quit()

    if not frames:
        raise RuntimeError("No frames could be extracted from PERSIANN-CCS.")

    data_cube = np.stack(frames, axis=0)  # (T, 100, 155)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.save(output_path, data_cube)

    logger.info(
        "Successfully saved 4km dataset! Shape: %s, Max: %.2f mm/hr -> %s",
        data_cube.shape, data_cube.max(), output_path
    )
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Download 4km PERSIANN-CCS satellite data for Assam")
    parser.add_argument("--year", type=int, default=2023, help="Year to download")
    parser.add_argument("--frames", type=int, default=168, help="Number of hourly frames (168 = 1 week)")
    parser.add_argument("--output", type=str, default=None, help="Output .npy path")
    args = parser.parse_args()

    download_persiann_frames(year=args.year, max_frames=args.frames, output_path=args.output)
