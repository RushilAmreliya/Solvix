"""
PERSIANN-CCS 4km Resolution Smart Convective Downloader
Downloads and crops hourly 4km satellite precipitation data for North-East India / Assam.

Resilience Architecture:
    - Long-term Wi-Fi/Internet recovery: if local network drops, pauses and waits up to 30 minutes
      until connection is restored, then resumes automatically.
    - Frequent disk checkpointing (every 10 frames): saves progress continuously so no downloaded
      hours are lost if the computer sleeps, reboots, or drops Wi-Fi.
    - Smart event filtering: continuous monsoon + targeted off-season storms with 3h pre / 2h post buffers.
"""
import argparse
from datetime import datetime
import ftplib
import gzip
import io
import logging
import os
import re
import sys
import time

import numpy as np
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("persiann.smart_fetch")

CHRS_FTP_HOST = "128.200.89.195"
FTP_BASE_DIR = "CHRSdata/PERSIANN-CCS/hrly"

# Assam 4km crop coordinates
ROW_START, ROW_END = 800, 900
COL_START, COL_END = 2245, 2400
TARGET_H, TARGET_W = 100, 155

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))

STATIONS = [
    ("Guwahati",  26.14, 91.74),
    ("Dibrugarh", 27.47, 94.91),
    ("Silchar",   24.82, 92.79),
]


def parse_filename_datetime(fname: str) -> datetime | None:
    """Extract UTC datetime from filename ending in yy_doy_hh.bin.gz."""
    m = re.search(r"(\d{2})(\d{3})(\d{2})\.bin\.gz$", fname)
    if m:
        yy, doy, hh = m.groups()
        try:
            return datetime.strptime(f"20{yy}_{doy}_{hh}", "%Y_%j_%H")
        except ValueError:
            return None
    return None


def get_off_season_storm_hours(start_date: str, end_date: str) -> set[str]:
    """Query Open-Meteo archive across Assam to flag all unseasonal rain events + buffer."""
    logger.info("Detecting off-season storms via historical station network (%s to %s)...", start_date, end_date)
    combined_mask = None
    times = []

    for name, lat, lon in STATIONS:
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
            f"&hourly=precipitation&timezone=UTC"
        )
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                precip = hourly.get("precipitation", [])
                rain = [p is not None and p > 0.1 for p in precip]
                if combined_mask is None:
                    combined_mask = rain
                else:
                    combined_mask = [a or b for a, b in zip(combined_mask, rain)]
        except Exception as exc:
            logger.warning("Station query failed for %s: %s", name, exc)

    buffered_hours = set()
    if combined_mask and times:
        for i, is_rain in enumerate(combined_mask):
            if is_rain:
                # 3 hours prior (-3) to 2 hours post (+2)
                for offset in range(-3, 3):
                    if 0 <= i + offset < len(combined_mask):
                        buffered_hours.add(times[i + offset])

    logger.info("Identified %d off-season storm & buffer hours.", len(buffered_hours))
    return buffered_hours


class FTPSession:
    """Persistent, self-healing FTP session with patient network reconnection."""

    def __init__(self, host: str = CHRS_FTP_HOST, timeout: int = 30):
        self.host = host
        self.timeout = timeout
        self.ftp: ftplib.FTP | None = None
        self.current_dir: str | None = None
        self.reconnect()

    def reconnect(self, max_retries: int = 60) -> None:
        """Retry connection patiently (up to ~30 mins) if local Wi-Fi drops."""
        for attempt in range(1, max_retries + 1):
            if self.ftp:
                try:
                    self.ftp.close()
                except Exception:
                    pass
            try:
                self.ftp = ftplib.FTP(self.host, timeout=self.timeout)
                self.ftp.login()
                self.ftp.set_pasv(True)
                if self.current_dir:
                    self.ftp.cwd(self.current_dir)
                return
            except Exception as exc:
                wait_s = min(15, 3 * attempt)
                logger.warning(
                    "Network unreachable / FTP retry %d/%d (%s). Waiting %ds for connection...",
                    attempt,
                    max_retries,
                    exc,
                    wait_s,
                )
                time.sleep(wait_s)
        raise ConnectionError("Unable to reconnect to CHRS FTP server after extended retries.")

    def cwd(self, path: str) -> None:
        self.current_dir = path
        try:
            self.ftp.cwd(path)
        except Exception:
            self.reconnect()
            self.ftp.cwd(path)

    def nlst(self) -> list[str]:
        try:
            return self.ftp.nlst()
        except Exception:
            self.reconnect()
            return self.ftp.nlst()

    def download_frame(self, fname: str, max_retries: int = 5) -> np.ndarray | None:
        for attempt in range(1, max_retries + 1):
            buf = io.BytesIO()
            try:
                self.ftp.retrbinary(f"RETR {fname}", buf.write)
                buf.seek(0)
                with gzip.GzipFile(fileobj=buf) as gz:
                    raw = gz.read()

                grid = np.frombuffer(raw, dtype=">i2").reshape((3000, 9000))
                precip = grid.astype(np.float32) / 100.0
                crop = precip[ROW_START:ROW_END, COL_START:COL_END]
                return np.where(crop < 0, 0.0, crop)
            except Exception as exc:
                logger.warning("Socket drop on %s (%s). Reconnecting (try %d/%d)...", fname, exc, attempt, max_retries)
                time.sleep(2)
                self.reconnect()
        logger.error("Failed to download %s after %d retries. Skipping frame.", fname, max_retries)
        return None

    def close(self) -> None:
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception:
                pass


def fetch_smart_persiann_range(
    start_date: str = "2023-05-01",
    end_date: str = "2026-07-31",
    output_master: str | None = None,
    max_frames: int | None = None,
) -> str:
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    years = list(range(start_dt.year, end_dt.year + 1))

    if output_master is None:
        output_master = os.path.join(
            OUTPUT_DIR,
            f"assam_persiann_4km_{start_dt.strftime('%Y%m')}_{end_dt.strftime('%Y%m')}_smart.npy",
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info("==================================================")
    logger.info("  PERSIANN-CCS 4km Smart Convective Downloader")
    logger.info("  Period: %s -> %s (Years: %s)", start_date, end_date, years)
    logger.info("  Strategy: Continuous Monsoon + Targeted Off-Season Storms (+3h/-2h buffer)")
    logger.info("  Target BBox: Assam (100 x 155 pixels @ 4 km)")
    logger.info("  Output Master: %s", output_master)
    logger.info("==================================================")

    off_season_hours = get_off_season_storm_hours(start_date, end_date)
    yearly_files_to_merge = []
    total_downloaded = 0

    session = FTPSession()

    for year in years:
        year_chunk_path = os.path.join(OUTPUT_DIR, f"assam_persiann_4km_smart_chunk_{year}.npy")

        year_dir = f"/{FTP_BASE_DIR}/{year}"
        session.cwd(year_dir)
        files = sorted(session.nlst())

        candidate_files = []
        for fname in files:
            if not fname.endswith(".bin.gz"):
                continue
            dt = parse_filename_datetime(fname)
            if dt is None or not (start_dt <= dt <= end_dt):
                continue

            iso_hour = dt.strftime("%Y-%m-%dT%H:00")
            is_monsoon = dt.month in [5, 6, 7, 8, 9]

            if is_monsoon or (iso_hour in off_season_hours):
                candidate_files.append((dt, fname))

        candidate_files.sort(key=lambda x: x[0])
        logger.info(
            "Year %d: Selected %d high-value convective storm frames (skipped dry days).",
            year,
            len(candidate_files),
        )

        if not candidate_files:
            continue

        # Load existing frames if resuming an incomplete year chunk
        year_frames = []
        start_idx = 0
        if os.path.exists(year_chunk_path):
            try:
                existing_arr = np.load(year_chunk_path)
                if len(existing_arr) >= len(candidate_files):
                    logger.info("Year %d chunk already complete (%d frames) — skipping.", year, len(existing_arr))
                    yearly_files_to_merge.append(year_chunk_path)
                    total_downloaded += len(existing_arr)
                    continue
                else:
                    year_frames = list(existing_arr)
                    start_idx = len(year_frames)
                    logger.info("Resuming year %d from frame %d / %d ...", year, start_idx, len(candidate_files))
            except Exception as e:
                logger.warning("Could not read chunk %s (%s). Restarting year %d.", year_chunk_path, e, year)
                year_frames = []
                start_idx = 0

        t0 = time.time()
        for idx in range(start_idx, len(candidate_files)):
            if max_frames and total_downloaded >= max_frames:
                logger.info("Reached requested max_frames limit (%d).", max_frames)
                break

            dt, fname = candidate_files[idx]
            crop = session.download_frame(fname)
            if crop is not None:
                year_frames.append(crop)
                total_downloaded += 1

            # Progress log every 10 frames
            if (idx + 1) % 10 == 0 or (idx + 1) == len(candidate_files):
                elapsed = time.time() - t0
                fps = (idx + 1 - start_idx) / elapsed if elapsed > 0 else 0
                remaining_sec = (len(candidate_files) - (idx + 1)) / fps if fps > 0 else 0
                logger.info(
                    "[%d] %d/%d frames (%.1f sec/frame | ETA: %.1f hrs) | Peak Rain: %.1f mm/hr",
                    year,
                    idx + 1,
                    len(candidate_files),
                    1.0 / fps if fps > 0 else 0,
                    remaining_sec / 3600.0,
                    crop.max() if crop is not None else 0.0,
                )

            # Continuous checkpoint save to disk every 10 frames
            if (idx + 1) % 10 == 0:
                np.save(year_chunk_path, np.stack(year_frames, axis=0))

        if year_frames:
            year_data = np.stack(year_frames, axis=0)
            np.save(year_chunk_path, year_data)
            logger.info("Saved complete year %d chunk: shape=%s to %s", year, year_data.shape, year_chunk_path)
            yearly_files_to_merge.append(year_chunk_path)

        if max_frames and total_downloaded >= max_frames:
            break

    session.close()

    if yearly_files_to_merge:
        logger.info("Merging %d chunk files into %s ...", len(yearly_files_to_merge), output_master)
        all_cubes = [np.load(f) for f in yearly_files_to_merge]
        final_dataset = np.concatenate(all_cubes, axis=0)
        np.save(output_master, final_dataset)

        default_target = os.path.join(OUTPUT_DIR, "assam_persiann_4km.npy")
        np.save(default_target, final_dataset)

        logger.info("==================================================")
        logger.info("  SMART DOWNLOAD COMPLETE!")
        logger.info("  Consolidated dataset shape: %s", final_dataset.shape)
        logger.info("  Max precipitation recorded: %.2f mm/hr", final_dataset.max())
        logger.info("  Saved to: %s", output_master)
        logger.info("  Active dataset updated: %s", default_target)
        logger.info("==================================================")
        return output_master
    else:
        logger.error("No frames were downloaded.")
        return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart bulk download PERSIANN-CCS 4km satellite data")
    parser.add_argument("--start", default="2023-05-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2026-07-31", help="End date YYYY-MM-DD")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional max frame limit")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    fetch_smart_persiann_range(
        start_date=args.start,
        end_date=args.end,
        max_frames=args.max_frames,
        output_master=args.output,
    )
