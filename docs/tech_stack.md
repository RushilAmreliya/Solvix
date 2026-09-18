# Technology Stack

To ensure a highly functional and robust prototype under hackathon time constraints, we have chosen a unified, Python-centric stack. This allows rapid development and seamless integration between data science components and the frontend.

## Backend & Data Processing
- **Language:** Python 3.10+
- **API Framework:** FastAPI (Fast, asynchronous, handles data streams effectively)
- **Meteorological Processing:** 
  - `MetPy` & `wradlib` (Radar processing and unit conversions)
  - `Xarray` (Multi-dimensional raster data handling)
  - `Rasterio` & `GeoPandas` (Geospatial data I/O)

## Nowcasting & Machine Learning
- **Primary Engine:** PySTEPS
  - *Why:* PySTEPS is an industry-standard, highly optimized library for optical flow and probabilistic nowcasting. It is computationally efficient and perfect for generating reliable 0-2 hour forecasts during a demo.
- **Secondary Engine (Enhancement):** PyTorch
  - *Why:* For integrating lightweight deep learning models (like a small ConvLSTM) to predict storm intensity changes, which optical flow alone cannot capture.

## Database
- **Relational & Spatial:** PostgreSQL with PostGIS
- **Why:** Essential for storing storm cell centroids, managing alert zones, and executing rapid spatial queries.

## Frontend Dashboard
- **Framework:** Streamlit
- **Map Rendering:** Folium or Leafmap (integrated via `streamlit-folium`)
- **Why:** Streamlit enables the team to build a highly interactive data dashboard entirely in Python in a fraction of the time it takes to build a full JavaScript single-page application. This minimizes context switching and accelerates prototype delivery.
- **Future Enhancement / Advanced Version:** React.js with Leaflet/Deck.gl (Can be adopted for production scale, but not required for the SIH prototype).
