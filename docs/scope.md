# Project Scope & Success Criteria

Given a compressed 3–4 week timeline for a student team, the scope is strictly defined to ensure a polished and reliable prototype.

## In-Scope (Must-Have for Prototype)
1. **Regional Focus:** A specific high-risk convective zone in India (Primary focus: North-East India / Assam region, roughly a 200x200 km bounding box).
2. **Data Simulator:** A robust backend script that replays a known historical severe weather event to simulate a live data feed.
3. **Core Nowcasting (PySTEPS):** Implementation of optical flow for reliable extrapolation (+1 to +2 hours) of radar reflectivity.
4. **Hazard Inference:** Threshold-based logic to convert radar/satellite values into specific hazard warnings (Hail Probability, Cloudburst thresholds).
5. **Interactive Dashboard:** A Streamlit-based web map displaying:
   - Regional boundaries and basemap.
   - Overlays of predicted radar reflectivity.
   - Dynamic hazard polygons (color-coded by severity).
   - Mock UI elements for countdown timers alerting specific coordinates.

## Out-of-Scope (Future Work / Enhancements)
- Pan-India operational deployment.
- Live, direct integration with classified IMD real-time APIs (handled via simulator).
- Heavy, complex deep learning models requiring multi-GPU clusters. We prioritize the optical flow baseline, treating deep learning as an optional enhancement.
- Complex frontend frameworks (React/Angular) are deferred in favor of Streamlit.

## Success Criteria for SIH Demo
- The Data Simulator flawlessly pushes new data frames every "simulated" 10 minutes.
- The PySTEPS engine processes the data and generates forecast frames in under 1 minute.
- The Streamlit dashboard visually updates, rendering clear hazard zones and effectively communicating the threat lead-time.
