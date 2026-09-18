# Development Roadmap

This highly compressed, milestone-based roadmap spans 3–4 weeks of intense development leading up to the hackathon demo.

## Milestone 1: Data pipeline & Simulation (Week 1)
- **Goal:** Secure data and simulate a live feed.
- **Tasks:**
  - Define the specific bounding box over the Assam / North-East region.
  - Acquire historical radar, INSAT, and lightning data for 1-2 major storm events.
  - Build the **Data Simulator** script to parse (MetPy/Xarray) and sequentially stream these data frames via FastAPI.

## Milestone 2: Core Nowcasting Engine (Week 2)
- **Goal:** Predict storm movement.
- **Tasks:**
  - Integrate PySTEPS to ingest the simulated radar data.
  - Compute optical flow and generate +1 and +2 hour forecast frames.
  - Develop the Hazard Products module (thresholding rules for hail, severe rain).
  - Expose the resulting forecast arrays as GIS-friendly formats (GeoJSON/Raster tiles) via FastAPI.

## Milestone 3: Streamlit Dashboard (Week 3)
- **Goal:** Visualize the predictions interactively.
- **Tasks:**
  - Setup the Streamlit application.
  - Integrate `folium` or `leafmap` to display the base map of the target region.
  - Fetch forecast outputs from the backend and render radar overlays and hazard polygons.
  - Implement interactive UI widgets (timeline sliders, location selection).

## Milestone 4: Integration, Testing & Demo Polish (Week 4)
- **Goal:** Ensure a flawless presentation.
- **Tasks:**
  - End-to-end testing: Run the simulator and verify the dashboard updates smoothly.
  - Refine UI aesthetics, add a countdown/alerting logic for a mock location.
  - (Optional) Integrate lightweight Deep Learning module for intensity adjustment if time permits.
  - Finalize the pitch, record backup demo videos, and practice the presentation.
