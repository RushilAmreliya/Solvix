# Convective Scale Nowcasting System (SIH26084)

A real-time, multi-source data fusion Nowcasting System for thunderstorms, hail, and cloudbursts.  
Developed for **Smart India Hackathon 2024** — Problem Statement SIH26084.

---

## Architecture

```
Data Simulator ──POST──▶ FastAPI Backend ──▶ PySTEPS Optical Flow (Primary)
                                          └──▶ CNN Enhancement   (Secondary, 30% blend)
                                          └──▶ Hazard Engine     (4 hazard products)
                                          └──▶ Streamlit Dashboard (GIS + Alerts)
```

## Project Structure

```text
.
├── docs/                        # System design, architecture, roadmap
├── data/
│   ├── README.md                # Data format documentation
│   └── assam_gpm_sample.npy     # NASA GPM IMERG historical data (Assam, May 2023)
├── src/
│   ├── backend/
│   │   ├── main.py              # FastAPI backend (PySTEPS + CNN + hazard serving)
│   │   └── simulator.py         # Historical data replay simulator (POSTs frames)
│   └── engine/
│       ├── nowcast_model.py     # Shared CNN model definition
│       ├── pysteps_engine.py    # PySTEPS optical flow wrapper (PRIMARY ENGINE)
│       ├── hazard_engine.py     # 4 hazard product functions + polygon generator
│       ├── fetch_gee_data.py    # NASA GPM data acquisition via Google Earth Engine
│       └── train.py             # CNN model training script
│   └── frontend/
│       └── app.py               # Streamlit GIS dashboard
├── requirements.txt
├── Procfile                     # Render deployment config
└── README.md
```

---

## How to Run (Full Demo)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (First time) Fetch Data
```bash
python -m src.engine.fetch_gee_data
```
> Requires a Google Earth Engine account. The pre-fetched `assam_gpm_sample.npy` is included for immediate use.

### 3. (First time) Train the CNN
```bash
python -m src.engine.train
```
> The pre-trained `nowcast_model.pth` is included. Re-run only if you change the architecture.

### 4. Start the Backend (Terminal 1)
```bash
uvicorn src.backend.main:app --reload
```

### 5. Start the Data Simulator (Terminal 2)
```bash
# Demo mode: 20× faster than real-time, loops continuously
python -m src.backend.simulator --speed 0.05 --loop
```

### 6. Start the Dashboard (Terminal 3)
```bash
streamlit run src/frontend/app.py
```

The dashboard auto-refreshes every 30 seconds.  
Open: http://localhost:8501

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/api/v1/ingest/frame` | Ingest a frame from the simulator |
| `GET`  | `/api/v1/forecast/latest` | Get forecast + 4 hazard products + storm ETAs |

Interactive Swagger docs: http://localhost:8000/docs

---

## Hazard Products

| Product | Threshold | Basis |
|---------|-----------|-------|
| Cloudburst Risk | ≥ 50 mm/hr | IMD: ≥ 100 mm / 3 hrs |
| Hail Probability | > 25 mm/hr | Deep convective cell proxy |
| Lightning Density | > 10 mm/hr | CG lightning correlation proxy |
| Downburst Risk | High intensity + gradient | Microburst signature proxy |

---

## Documentation

See `/docs` for full system design, architecture diagrams, data sources, and development roadmap.
