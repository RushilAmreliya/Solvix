# Data Directory

## `assam_gpm_sample.npy`

Historical NASA GPM IMERG precipitation data for the Assam region.

| Property      | Value                                       |
|---------------|---------------------------------------------|
| **Shape**     | `(T, H, W)` — typically `(336, 24, 49)` for 1 week of half-hourly data |
| **T**         | Number of time steps (336 = 7 days × 48 frames/day) |
| **H × W**     | Spatial grid over `[24°N–28°N, 89.8°E–96°E]` at ~0.1° resolution |
| **Units**     | `mm/hr` (calibrated precipitation rate — `precipitationCal` band) |
| **Source**    | NASA GPM IMERG V06 Half-Hourly (`NASA/GPM_L3/IMERG_V06`) via Google Earth Engine |
| **Coverage**  | 2023-05-01 to 2023-05-07 (pre-monsoon active convection period, Assam) |
| **Fetched by**| `src/engine/fetch_gee_data.py`              |

## Regenerating the data

```bash
python -m src.engine.fetch_gee_data
```

This will authenticate with Google Earth Engine and download fresh data into this directory.
Requires a valid GEE project ID (see `fetch_gee_data.py` for setup instructions).
