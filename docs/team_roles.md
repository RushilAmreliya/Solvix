# Team Roles & Responsibilities

For a 6-member SIH team executing a rapid 3-4 week sprint, clear delegation is critical.

1. **Team Leader / Product Manager (1)**
   - Manages milestones and roadmap execution.
   - Prepares presentation materials, handles documentation, and ensures alignment with SIH requirements.
   - Coordinates cross-module integration.

2. **Meteorological Data Engineer (1)**
   - Focus: Data Ingestion, Simulation & Preprocessing.
   - Responsibilities: Building the Data Simulator, handling NetCDF/HDF5 parsing using Xarray and MetPy, ensuring data quality.

3. **Nowcasting Engine Developer (2)**
   - Focus: The Core Prediction Logic.
   - Responsibilities: Implementing PySTEPS for optical flow, developing hazard threshold algorithms, and optionally exploring lightweight ML enhancements.

4. **Backend API Developer (1)**
   - Focus: FastAPI Server & Geo-data pipeline.
   - Responsibilities: Building endpoints to serve simulator data and forecast outputs, handling PostGIS queries, and formatting data as GeoJSON.

5. **Dashboard Developer (Streamlit / Python) (1)**
   - Focus: Interactive GIS Visualization.
   - Responsibilities: Building the Streamlit frontend, implementing Folium/Leafmap, rendering raster layers and hazard polygons, and creating the alert UI.
