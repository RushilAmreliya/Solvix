# NowCast Fusion — Command Center Dashboard

A real-time GIS situational awareness dashboard built with React 19, Vite, Tailwind CSS, and Leaflet. Designed for meteorologists and disaster response teams monitoring convective storm hazards across North-East India (Assam Region).

---

## Key Features

- **Real-Time WebSocket Feed (`ws://localhost:8000/ws/forecast`)**:
  - Live 60 FPS frame streaming and low-latency nowcast updates.
  - Automatic reconnection logic with live ping indicator.
- **Interactive Leaflet GIS Map**:
  - Bound strictly to the Assam domain (`24.0°N–28.0°N, 89.8°E–96.0°E`).
  - Esri Dark Canvas and Satellite basemaps.
  - Transparent precipitation overlays with live colorbars.
  - Live Doppler radar tiles via RainViewer API (with smooth tile fallback).
  - IMD hazard polygons (Cloudburst, Hail, Lightning, Downburst).
- **Early Warning & Hazard Intelligence**:
  - 4 automated IMD convective hazard monitors.
  - Storm arrival countdown clock for key cities (Guwahati, Silchar, Dibrugarh, etc.).
  - Thermodynamic atmospheric context (CAPE, Lifted Index, 10m wind shear) powered by Open-Meteo.
  - User geolocation support with local threat assessment.
- **Playback & Lead-Time Controls**:
  - Lead-time slider: Current, +30 min, +60 min, +90 min, +3 hr, +6 hr.
  - Play/Pause animation with loop toggle.

---

## Tech Stack

- **Framework**: React 19 + Vite 8
- **Styling**: Tailwind CSS v4 + Lucide React icons
- **GIS / Mapping**: Leaflet + React-Leaflet
- **Networking**: WebSocket API + Axios / Fetch

---

## Development Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server (accessible over LAN at http://0.0.0.0:5173)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```
