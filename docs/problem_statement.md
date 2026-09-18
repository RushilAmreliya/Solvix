# Problem Statement: Convective Scale Nowcasting

## Background
Convective storms—such as severe thunderstorms, hail, downburst winds, and cloudbursts—are among India’s deadliest natural hazards. These events are characterized by rapid onset, highly localized impacts, and extreme intensity. They pose significant risks to agriculture, aviation, power distribution, and human life, particularly in highly vulnerable areas like North-East India.

## Why Traditional Systems Fail
Traditional Numerical Weather Prediction (NWP) models are inadequate for convective storms due to several limitations:
- **Spatial Resolution:** Global or regional models operate at a resolution of 10-25 km, missing the 1-5 km scale at which these storms develop.
- **Temporal Lag:** NWP models take hours to compute. Convective cells can develop, mature, and dissipate within 30 to 60 minutes.
- **Physics Limitations:** The parametrization of convection in traditional models is an approximation, which often fails to capture the chaotic and explosive nature of real-time storm initiation.

## Official Requirements (SIH26084)
We must build a real-time, multi-source data fusion-based Nowcasting System that:
1. **Ingests Multi-Modal Data:** Doppler Weather Radar (reflectivity + velocity), INSAT-3D/3DR (thermal/infrared), and ground-based lightning network data.
2. **Detects Early Initiation:** Identifies the early stages of convective initiation before severe impacts occur.
3. **Forecasts Hazards:** Predicts specific convective hazards including:
   - Lightning strike density
   - Hail probability
   - Downburst velocity
   - Cloudburst thresholds
4. **Resolution & Lead Time:** Operates at 1–3 km spatial resolution with a 0–6 hour lead time.
5. **Interactive Dashboard:** Displays results on a real-time interactive GIS dashboard featuring live hazard zones and countdown clocks for storm arrival.

*Note: For the prototype, the primary geographic focus will be high-risk convective zones in India, specifically the North-East India / Assam region, due to its operational importance and high frequency of severe weather events.*
