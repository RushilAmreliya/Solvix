import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, ImageOverlay, Polygon, Tooltip, useMap } from 'react-leaflet';
import { CloudRain, Zap, CloudSnow, Wind, RefreshCcw } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import './index.css';

const API_URL = "http://localhost:8000/api/v1/forecast/latest";
const BOUNDS = [[24.0, 89.8], [28.0, 96.0]];
const MAP_CENTER = [26.0, 93.0];

// Helper to auto-fit the processing bounds exactly into the map card
function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (map && bounds) {
      map.fitBounds(bounds, { padding: [12, 12], animate: false });
    }
  }, [map, bounds]);
  return null;
}

// Inverted polygon to dim out everything outside the processing area
const WORLD_BOUNDS = [
  [-90, -360],
  [90, -360],
  [90, 360],
  [-90, 360]
];
const MASK_POSITIONS = [
  WORLD_BOUNDS,
  [
    [24.0, 89.8],
    [28.0, 89.8],
    [28.0, 96.0],
    [24.0, 96.0]
  ]
];

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('current');
  const [activeHazard, setActiveHazard] = useState('cloudburst');

  const fetchData = async () => {
    try {
      const response = await fetch(API_URL);
      if (!response.ok) throw new Error("Failed to fetch data");
      const jsonData = await response.json();
      setData(jsonData);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 1000); // 1-second auto refresh for 60fps fast backend
    return () => clearInterval(interval);
  }, []);

  if (!data) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">
      <div className="flex items-center space-x-3 text-xl">
        <RefreshCcw className="animate-spin text-blue-500" size={32} />
        <span>Waiting for backend data...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans p-6">
      <header className="mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-3xl font-bold text-white flex items-center">
          <CloudRain className="text-blue-500 mr-3" size={36} /> 
          NowCast Fusion
        </h1>
        <p className="text-gray-400 mt-2">Real-time Convective Hazard Early Warning System (React 60FPS Edition)</p>
      </header>

      {/* Storm Cell Alerts */}
      {data.storm_cells && data.storm_cells.length > 0 && (
        <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
          {data.storm_cells.map((cell, idx) => (
            <div key={idx} className="bg-red-950/40 border border-red-500 rounded-lg p-4">
              <h3 className="font-bold text-lg text-white">📍 {cell.city}</h3>
              <p className="text-gray-300 mt-1">🕐 ETA: <span className="text-white font-bold">{cell.eta_minutes} min</span></p>
              <p className="text-gray-300">🌧️ Intensity: <span className="text-red-400 font-bold">{cell.intensity.toFixed(1)} mm/hr</span></p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Precipitation Map */}
        <div className="bg-gray-900 rounded-xl overflow-hidden border border-gray-800 shadow-xl">
          <div className="p-4 bg-gray-800 flex justify-between items-center">
            <h2 className="text-xl font-bold">📡 Precipitation Forecast</h2>
            <div className="flex space-x-2">
              {['current', 'f30', 'f60', 'f90'].map((tab, i) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab ? 'bg-blue-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                >
                  {i === 0 ? 'Current' : `+${i * 30} min`}
                </button>
              ))}
            </div>
          </div>
          <div className="h-[500px] w-full relative">
            <MapContainer 
              bounds={BOUNDS}
              boundsOptions={{ padding: [12, 12] }}
              maxBounds={BOUNDS}
              maxBoundsViscosity={1.0}
              scrollWheelZoom={true} 
              className="h-full w-full bg-[#0a0a0a]" 
              style={{ background: '#0f172a' }}
            >
              <FitBounds bounds={BOUNDS} />
              {/* Using a more realistic map layout */}
              <TileLayer 
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png" 
                attribution="&copy; OpenStreetMap & CartoDB" 
              />
              <Polygon positions={MASK_POSITIONS} pathOptions={{ color: 'none', fillColor: '#000', fillOpacity: 0.8 }} />
              {data.images && data.images[activeTab] && (
                <ImageOverlay url={data.images[activeTab]} bounds={BOUNDS} opacity={1} />
              )}
            </MapContainer>
          </div>
        </div>

        {/* Hazard Map */}
        <div className="bg-gray-900 rounded-xl overflow-hidden border border-gray-800 shadow-xl">
          <div className="p-4 bg-gray-800 flex justify-between items-center">
            <h2 className="text-xl font-bold">🎯 Hazard Products</h2>
            <div className="flex space-x-2">
              {['cloudburst', 'hail', 'lightning', 'downburst'].map((hazard) => (
                <button
                  key={hazard}
                  onClick={() => setActiveHazard(hazard)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors capitalize ${
                    activeHazard === hazard ? 'bg-red-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                >
                  {hazard}
                </button>
              ))}
            </div>
          </div>
          <div className="h-[500px] w-full relative">
            <MapContainer 
              bounds={BOUNDS}
              boundsOptions={{ padding: [12, 12] }}
              maxBounds={BOUNDS}
              maxBoundsViscosity={1.0}
              scrollWheelZoom={true} 
              className="h-full w-full bg-[#0a0a0a]" 
              style={{ background: '#0f172a' }}
            >
              <FitBounds bounds={BOUNDS} />
              <TileLayer 
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png" 
                attribution="&copy; OpenStreetMap & CartoDB" 
              />
              <Polygon positions={MASK_POSITIONS} pathOptions={{ color: 'none', fillColor: '#000', fillOpacity: 0.8 }} />
              {data.images && data.images[activeHazard] && (
                <ImageOverlay url={data.images[activeHazard]} bounds={BOUNDS} opacity={1} />
              )}
              {activeHazard === 'cloudburst' && data.cloudburst_polygons?.map((poly, i) => (
                <Polygon key={i} positions={poly.bounds} pathOptions={{ color: '#ef4444', weight: 2, fillColor: '#ef4444', fillOpacity: 0.3 }}>
                  <Tooltip>Cloudburst Risk: {(poly.risk * 100).toFixed(0)}%</Tooltip>
                </Polygon>
              ))}
              {activeHazard === 'lightning' && data.lightning_polygons?.map((poly, i) => (
                <Polygon key={i} positions={poly.bounds} pathOptions={{ color: '#f59e0b', weight: 2, fillColor: '#f59e0b', fillOpacity: 0.3 }}>
                  <Tooltip>Lightning Risk: {(poly.risk * 100).toFixed(0)}%</Tooltip>
                </Polygon>
              ))}
            </MapContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
