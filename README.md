# Convective Scale Nowcasting System (SIH26084)

A real-time, multi-source data fusion Nowcasting System for thunderstorms, hail, downbursts, and cloudbursts across North-East India (Assam Region).  
Developed for **Smart India Hackathon** — Problem Statement SIH26084.

---

## Architecture Overview

```text
Data Simulator ──POST──▶ FastAPI Backend (Lifespan + WS) ──▶ PySTEPS Optical Flow (Primary)
                                                        └──▶ U-Net Enhancement (30% blend)
                                                        └──▶ Hazard Engine (4 IMD Products)
                                                        └──▶ SRTM 1km Orographic Downscaling
                                                        └──▶ React 19 Dashboard (60FPS + WebSocket)
                                                        └──▶ Streamlit Dashboard (Folium GIS)
```

---

## Project Structure

```text
.
├── notebooks/                   # Jupyter notebooks for model training & exploration
│   ├── train_on_colab.ipynb     # Google Colab U-Net training pipeline
│   └── README.md                # Guide for running on Colab GPU
├── scripts/                     # Standalone utility & data automation scripts
│   ├── setup_credentials.py     # NASA Earthdata credentials setup
│   ├── start_download.bat       # PERSIANN-CCS multi-year data downloader
│   └── README.md                # Scripts reference guide
├── backend/                     # High-performance FastAPI server & scientific engines
│   ├── main.py                  # REST + WebSocket endpoints & background tasks
│   ├── settings.py              # Pydantic BaseSettings & configuration
│   ├── simulator.py             # Event stream simulator (Satellite & Doppler radar)
│   └── engine/
│       ├── alert_engine.py      # Hazard alerts & IMD threshold classification
│       ├── fetch_earthdata.py   # NASA Earthdata satellite client
│       ├── fetch_gee_data.py    # Google Earth Engine precipitation client
│       ├── fetch_persiann.py    # PERSIANN-CCS 4km downloader
│       ├── hazard_engine.py     # Cloudburst, Hail, Lightning, Downburst algorithms
│       ├── live_radar_engine.py # Live RainViewer tile composite & rain rate ingestion
│       ├── nowcast_model.pth    # Bundled pre-trained U-Net weights
│       ├── nowcast_model.py     # PyTorch UNetNowcast neural network
│       ├── openmeteo_engine.py  # Atmospheric thermodynamic context (CAPE, wind shear)
│       ├── pysteps_engine.py    # Lucas-Kanade optical flow extrapolation
│       ├── radar_loader.py      # Doppler polar sweep conversion
│       ├── rendering.py         # Transparent geospatial PNG map rendering
│       ├── terrain_downscale.py # SRTM 90m DEM downscaling to 1 km
│       └── train.py             # PyTorch training loop with RainWeightedLoss
├── frontend/                    # Modern React 19 + Vite + Leaflet GIS Dashboard
│   ├── src/
│   │   ├── App.jsx              # Command Center UI (WebSocket, GIS map, alerts)
│   │   ├── App.css
│   │   ├── index.css            # Tailwind styles
│   │   └── main.jsx
│   ├── package.json
│   ├── streamlit_app.py         # Alternative lightweight Streamlit/Folium dashboard
│   └── README.md
├── data/                        # Satellite cubes & topographic elevation models
│   ├── assam_persiann_4km.npy   # High-resolution (4km) PERSIANN-CCS dataset
│   ├── assam_gpm_sample.npy     # Benchmark NASA GPM IMERG 10km grid
│   ├── srtm_assam.npy           # NASA SRTM topography grid
│   └── README.md
├── docs/                        # Scientific, architecture, and design specifications
│   ├── architecture.md
│   ├── data_sources.md
│   ├── development_roadmap.md
│   ├── idea_summary.md
│   ├── problem_statement.md
│   ├── scope.md
│   ├── team_roles.md
│   └── tech_stack.md
├── tests/                       # Complete pytest unit and integration test suite
│   ├── test_backend_fixes.py    # Live radar, caching, polar rasterization tests
│   ├── test_hazard_engine.py    # IMD threshold & convective proxy tests
│   ├── test_model_and_api.py    # U-Net forward pass, CSI/ETS metrics, API tests
│   └── test_pysteps_engine.py   # Unit conversion & persistence fallback tests
├── .env.example                 # Backend environment variable template
├── .gitignore                   # Git ignore rules for data chunks & caches
├── Procfile                     # Cloud deployment configuration
├── requirements.txt             # Python dependencies
└── start_local.bat              # 1-click Windows launcher (FastAPI + Simulator + React)
```

---

## Scientific Foundations & Lead Time Skill

- **Lead times +30 to +90 min (Operational Skill):** High forecast skill achieved via PySTEPS Lucas-Kanade optical flow in logarithmic dBR reflectivity space, augmented with a 30% blend from `UNetNowcast` for intensity evolution.
- **Lead times +3 hr to +6 hr (Kinematic Trend Outlook):** Available in the dashboard for broad advection and synoptic awareness. *Caveat: Kinematic extrapolation skill degrades beyond 2 hours due to convective initiation and cell dissipation.*
- **Thermodynamic Adjustments:** Live CAPE (Convective Available Potential Energy) and 10m wind shear from Open-Meteo dynamically adjust hail probability and microburst/downburst risks.
- **Orographic Downscaling:** SRTM 90m digital elevation model enhances precipitation fields over Assam's complex mountain topography at ~1 km resolution.

---

## Quick Start (Windows 1-Click Launcher)

Double-click `start_local.bat` in the project root to instantly spin up:
1. FastAPI backend server (`http://localhost:8000`)
2. Data simulator streaming live 60 FPS weather frames
3. React 19 GIS Command Center dashboard (`http://localhost:5173`)

---

## Manual Setup & Step-by-Step Execution

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
```

### 3. Run Automated Tests
Verify all 28 scientific, machine learning, and API tests pass:
```bash
pytest tests/ -v
```

### 4. Train the U-Net Model (Optional)
A pre-trained checkpoint (`backend/engine/nowcast_model.pth`) is bundled with the repository.  
To retrain locally or view CSI/ETS skill metrics:
```bash
python -m backend.engine.train
```
To train on Google Colab with GPU acceleration, use `notebooks/train_on_colab.ipynb`.

### 5. Download Additional Satellite Data (Optional)
To fetch multi-year 4km PERSIANN-CCS data:
```bash
scripts\start_download.bat
# or
python -m backend.engine.fetch_persiann --start 2023-05-01 --end 2026-07-31
```

### 6. Start the Backend (Terminal 1)
```bash
uvicorn backend.main:app --reload --port 8000
```
- Interactive Swagger documentation: http://localhost:8000/docs  
- WebSocket endpoint: `ws://localhost:8000/ws/forecast`

### 7. Start the Data Simulator (Terminal 2)

**Option A: Stream Satellite Precipitation (4km PERSIANN / 10km GPM)**
```bash
python -m backend.simulator --source satellite --fps 60 --loop
```

**Option B: Stream Doppler Weather Radar Sweeps (dBZ + Velocity)**
```bash
python -m backend.simulator --source radar --radar-site Guwahati --fps 2 --loop
```

### 8. Launch the Frontend

**Option A: React 19 GIS Command Center (Recommended)**
```bash
cd frontend
npm install
npm run dev
```
Open: http://localhost:5173 (or http://localhost:5173 across LAN)

**Option B: Streamlit Dashboard**
```bash
streamlit run frontend/streamlit_app.py
```
Open: http://localhost:8501

---

## API & WebSocket Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Health check, buffer status, and model metadata |
| `POST` | `/api/v1/ingest/frame` | Ingest a Cartesian precipitation frame from sensor/simulator |
| `POST` | `/api/v1/ingest/radar-sweep` | Ingest raw Doppler Weather Radar polar sweep (dBZ + velocity) |
| `POST` | `/api/v1/ingest/sync-live-radar` | Trigger on-demand sync with live RainViewer/IMD radar |
| `GET`  | `/api/v1/forecast/latest` | Retrieve current forecast, 4 hazard layers, and storm ETAs |
| `WS`   | `/ws/forecast` | Real-time bi-directional WebSocket push feed |

---

## Hazard Products & IMD Criteria

| Product | Threshold | Meteorological Basis |
|---------|-----------|----------------------|
| **Cloudburst Risk** | ≥ 50 mm/hr | IMD definition: ≥ 100 mm in ≤ 3 hrs (sustained severe cloudburst) |
| **Hail Probability** | > 25 mm/hr + CAPE | Deep convective core proxy scaled by Convective Available Potential Energy |
| **Lightning Density** | > 10 mm/hr | Updraft convective proxy for Cloud-to-Ground (CG) discharge |
| **Downburst / Microburst Risk** | High intensity + spatial gradient + wind shear | Rapid downdraft proxy enhanced by surface 10m wind speed |
