# Data Directory

This directory stores satellite precipitation data cubes and topographic digital elevation models (DEM) for the North-East India (Assam) domain: `[24.0°N–28.0°N, 89.8°E–96.0°E]`.

---

## Datasets

### 1. `assam_persiann_4km.npy` (Primary High-Resolution Grid)
Multi-year high-resolution precipitation observations from NOAA/CHRS PERSIANN-CCS.
- **Resolution**: 0.04° (~4 km grid spacing), 100 × 155 spatial grid.
- **Temporal Cadence**: 1-hour intervals across pre-monsoon and monsoon convective seasons (2023–2026).
- **Units**: `mm/hr` (instantaneous rain rate).
- **Download Script**:
  ```bash
  scripts\start_download.bat
  # or
  python -m backend.engine.fetch_persiann --start 2023-05-01 --end 2026-07-31
  ```

### 2. `assam_gpm_sample.npy` (Benchmark Grid)
Historical NASA GPM IMERG V06 precipitation data.
- **Shape**: `(336, 24, 49)` (7 days of half-hourly observations).
- **Resolution**: ~0.1° (~10 km grid spacing).
- **Units**: `mm/hr` (calibrated precipitation rate — `precipitationCal` band).
- **Fetched by**: `backend/engine/fetch_gee_data.py` or `backend/engine/fetch_earthdata.py`.

### 3. `srtm_assam.npy` (Topographic Elevation)
NASA SRTM 90m Digital Elevation Model downscaled to the Assam grid.
- **Use Case**: Used by `backend/engine/terrain_downscale.py` for orographic enhancement and ridge precipitation downscaling.

---

## Intermediate Files

Intermediate yearly chunks (`assam_persiann_4km_smart_chunk_*.npy`) generated during download are automatically ignored by git to keep the repository lightweight.
