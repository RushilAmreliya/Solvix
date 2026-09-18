# Data Sources (Prototype Development)

To build a reliable prototype, we rely on open-source historical datasets and simulated data streams, focusing on high-risk convective zones in India (primary focus: North-East India / Assam region).

## 1. Doppler Weather Radar
- **Source:** Given IMD's real-time API restrictions, we will use historical radar dumps. If local Indian radar data (e.g., Mohanbari/Guwahati radar) is unavailable for training, we will use AWS NEXRAD Level II open data as a structural stand-in to build our processing pipelines, adapting the parsers for IMD formats.
- **Access:** `s3://noaa-nexrad-level2` via `boto3` or sample IMD NetCDF files.

## 2. INSAT-3D/3DR Satellite Data
- **Source:** MOSDAC (Meteorological and Oceanographic Satellite Data Archival Centre) by ISRO.
- **Prototype Dataset:** Thermal Infrared (TIR) and Water Vapor (WV) channels over the North-East region.
- **Access:** Registered bulk downloads (HDF5 format).

## 3. Lightning Data
- **Source:** NASA LIS (Lightning Imaging Sensor), Global Hydrology Resource Center (GHRC), or community networks like Blitzortung.
- **Prototype Dataset:** Historical strikes mapped over the target region.

## The Data Simulator Approach
For the SIH Demonstration, we will build a **Data Simulator Script**.
- **What it does:** Replays a severe historical storm event (e.g., a major squall line in Assam) chronologically, feeding data to the FastAPI backend as if it were happening live.
- **Why:** This ensures the dashboard always has active, severe weather to process and display during judging, guaranteeing a flawless, realistic demonstration without depending on live, unpredictable weather APIs.
