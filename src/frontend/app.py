import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="NowCast Fusion", layout="wide")

st.title("🌩️ NowCast Fusion: Convective Hazard Early Warning")
st.markdown("Real-time AI nowcasting for North-East India (Assam Region).")

API_BASE_URL = "http://127.0.0.1:8000"

def fetch_data():
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/forecast/latest")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None

data = fetch_data()

if data and "error" not in data:
    # Convert lists back to Numpy arrays
    current_map = np.array(data["current_rain_map"])
    predicted_map = np.array(data["predicted_rain_map"])
    time_step = data["time_step"]
    
    # ==========================================
    # Map Coloring Logic
    # ==========================================
    # We use a jet colormap (blue=light rain, red=heavy rain)
    cmap = plt.get_cmap('jet')
    
    def colorize_rain(array):
        # Cap visualization at 20 mm/hr for better contrast
        normed = np.clip(array / 20.0, 0, 1) 
        rgba = cmap(normed)
        # Make areas with less than 0.5 mm/hr completely transparent
        rgba[array < 0.5, 3] = 0 
        # Make rainy areas semi-transparent so we can see the map underneath
        rgba[array >= 0.5, 3] = 0.6 
        return rgba
        
    img_current = colorize_rain(current_map)
    img_predicted = colorize_rain(predicted_map)
    
    # Geographic bounds for Assam
    bounds = [[24.0, 89.8], [28.0, 96.0]]
    map_center = [26.0, 93.0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"Current Weather (Time Step: {time_step})")
        m1 = folium.Map(location=map_center, zoom_start=6, tiles="CartoDB dark_matter")
        folium.raster_layers.ImageOverlay(
            image=img_current,
            bounds=bounds,
            interactive=True,
            cross_origin=False,
            zindex=1
        ).add_to(m1)
        st_folium(m1, width=700, height=500, key="map_current")
        
    with col2:
        st.subheader("AI Prediction (+30 mins)")
        m2 = folium.Map(location=map_center, zoom_start=6, tiles="CartoDB dark_matter")
        folium.raster_layers.ImageOverlay(
            image=img_predicted,
            bounds=bounds,
            interactive=True,
            cross_origin=False,
            zindex=1
        ).add_to(m2)
        st_folium(m2, width=700, height=500, key="map_predicted")
        
    # ==========================================
    # Hazard Alert Engine
    # ==========================================
    st.markdown("---")
    st.subheader("Automated Hazard Analysis")
    
    max_rain = np.max(predicted_map)
    
    if max_rain > 15:
        st.error(f"🔴 **CRITICAL ALERT: Cloudburst / Flash Flood Risk Detected.** Peak predicted intensity: {max_rain:.1f} mm/hr.")
    elif max_rain > 5:
        st.warning(f"🟠 **MODERATE ALERT: Heavy Thunderstorms Detected.** Peak predicted intensity: {max_rain:.1f} mm/hr.")
    else:
        st.success(f"🟢 **ALL CLEAR.** No severe convective hazards predicted. Peak predicted intensity: {max_rain:.1f} mm/hr.")
        
    if st.button("Simulate Next 30 Minutes (Refresh)"):
        st.rerun()

else:
    st.error("Cannot connect to AI Backend. Ensure `uvicorn src.backend.main:app` is running.")
