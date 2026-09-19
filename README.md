# Convective Scale Nowcasting System (SIH26084)

A real-time, multi-source data fusion Nowcasting System for thunderstorms, hail, downbursts, and cloudbursts.  
Developed for **Smart India Hackathon** — Problem Statement SIH26084.

---

## Architecture Overview

```
Data Simulator ──POST──▶ FastAPI Backend (Lifespan + WS) ──▶ PySTEPS Optical Flow (Primary)
                                                        └──▶ U-Net Enhancement (30% blend)
                                                        └──▶ Hazard Engine (4 IMD Products)
                                                        └──▶ SRTM 1km Orographic Downscaling
                                                        └──▶ React 19 Dashboard (60FPS + WebSocket)
                                                        └──▶ Streamlit Dashboard (Folium GIS)
```

## Project Structure

```text
.
├── docs/                        # System architecture, scientific scope, data sources
├── data/                        # Sample satellite cubes (4km PERSIANN / 10km GPM)
│   ├── assam_persiann_4km.npy
│   └── assam_gpm_sample.npy
├── backend/
│   ├── main.py                  # FastAPI REST + WebSocket backend
│   ├── settings.py              # Pydantic BaseSettings & .env management
│   ├── simulator.py             # Historical event stream simulator
│   └── engine/
│       ├── nowcast_model.py     # UNetNowcast deep learning architecture
│       ├── pysteps_engine.py    # PySTEPS Lucas-Kanade optical flow extrapolation
│       ├── hazard_engine.py     # 4 convective hazard algorithms + GeoJSON polygons
│       ├── rendering.py         # Transparent geospatial PNG map rendering
│       ├── openmeteo_engine.py  # Real-time CAPE & wind thermodynamic context
│       ├── terrain_downscale.py # SRTM 90m DEM downscaling to 1 km
│       └── train.py             # U-Net model training script with CSI/ETS metrics
├── frontend/                    # Modern React 19 + Vite + Leaflet dashboard
│   ├── src/
│   │   ├── App.jsx              # Real-time WebSocket + Leaflet GIS UI
│   │   └── index.css            # Tailwind styles
│   └── package.json
├── tests/                       # Complete pytest unit and integration test suite
│   ├── test_hazard_engine.py    # IMD threshold & proxy tests
│   ├── test_pysteps_engine.py   # Unit conversion & persistence fallback tests
│   └── test_model_and_api.py    # U-Net forward pass, CSI/ETS, and API tests
├── .env.example                 # Backend environment variable template
├── requirements.txt             # Python dependencies
└── Procfile                     # Deployment configuration
```

---

## Scientific Foundations & Lead Time Skill

- **Lead times +30 to +90 min (Operational Skill):** High forecast skill achieved via PySTEPS Lucas-Kanade optical flow in logarithmic dBR reflectivity space, augmented with a 30% blend from `UNetNowcast` for intensity evolution.
- **Lead times +3 hr to +6 hr (Kinematic Trend Outlook):** Available in the dashboard for broad advection and synoptic awareness. *Caveat: Kinematic extrapolation skill degrades beyond 2 hours due to convective initiation and cell dissipation.*
- **Thermodynamic Adjustments:** Live CAPE (Convective Available Potential Energy) and 10m wind shear from Open-Meteo dynamically adjust hail probability and microburst/downburst risks.
- **Orographic Downscaling:** SRTM 90m digital elevation model enhances precipitation fields over Assam's complex mountain topography at ~1 km resolution.

---

## How to Run

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
```

### 3. Run Automated Tests
Verify all 15 scientific and API tests pass:
```bash
pytest tests/ -v
```

### 4. Train the U-Net Model (Optional)
A pre-trained checkpoint is bundled. To retrain with the new U-Net architecture and view CSI/ETS skill metrics:
```bash
python -m backend.engine.train
```

### 5. Start the Backend (Terminal 1)
```bash
uvicorn backend.main:app --reload --port 8000
```
Interactive Swagger documentation: http://localhost:8000/docs  
WebSocket endpoint: `ws://localhost:8000/ws/forecast`

### 6. Start the Data Simulator (Terminal 2)

**Option A: Stream Satellite Precipitation (4km PERSIANN / 10km GPM)**
```bash
python -m backend.simulator --source satellite --fps 60 --loop
```

**Option B: Stream Doppler Weather Radar Sweeps (dBZ + Velocity)**
```bash
python -m backend.simulator --source radar --radar-site Guwahati --fps 2 --loop
```

### 7. Launch the Frontend

**Option A: React 19 GIS Dashboard (Recommended)**
```bash
cd frontend
npm install
npm run dev
```
Open: http://localhost:5173

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
