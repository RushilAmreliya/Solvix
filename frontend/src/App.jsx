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

      {/* Atmospheric Context Cards */}
      {data.atmospheric_context && (
        <div className="mb-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-yellow-600/40 rounded-xl p-4">
            <p className="text-yellow-400 text-xs font-semibold uppercase tracking-wider mb-1">⚡ CAPE</p>
            <p className="text-2xl font-bold text-white">{data.atmospheric_context.cape?.toFixed(0) ?? '--'}</p>
            <p className="text-gray-400 text-xs">J/kg — Storm Energy</p>
            <div className={`mt-2 text-xs font-medium ${data.atmospheric_context.cape > 2000 ? 'text-red-400' : data.atmospheric_context.cape > 1000 ? 'text-yellow-400' : 'text-green-400'}`}>
              {data.atmospheric_context.cape > 2000 ? '🔴 Extreme convection' : data.atmospheric_context.cape > 1000 ? '🟡 Active convection' : '🟢 Stable'}
            </div>
          </div>
          <div className="bg-gray-900 border border-blue-600/40 rounded-xl p-4">
            <p className="text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">💨 Wind Speed</p>
            <p className="text-2xl font-bold text-white">{data.atmospheric_context.wind_speed?.toFixed(1) ?? '--'}</p>
            <p className="text-gray-400 text-xs">m/s @ 10m AGL</p>
            <p className="text-gray-500 text-xs mt-2">Dir: {data.atmospheric_context.wind_direction?.toFixed(0) ?? '--'}°</p>
          </div>
          <div className="bg-gray-900 border border-cyan-600/40 rounded-xl p-4">
            <p className="text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">💧 Humidity</p>
            <p className="text-2xl font-bold text-white">{data.atmospheric_context.humidity?.toFixed(0) ?? '--'}%</p>
            <p className="text-gray-400 text-xs">2m Relative Humidity</p>
          </div>
          <div className="bg-gray-900 border border-purple-600/40 rounded-xl p-4">
            <p className="text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">📡 Data Source</p>
            <p className="text-lg font-bold text-white capitalize">{data.atmospheric_context.source ?? '--'}</p>
            <p className="text-gray-400 text-xs">Atmospheric context</p>
            <p className="text-gray-500 text-xs mt-2">SRTM: {data.srtm_loaded ? '✅ 1km' : '⏳ loading'}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Precipitation Map */}
        <div className="bg-gray-900 rounded-xl overflow-hidden border border-gray-800 shadow-xl">
          <div className="p-4 bg-gray-800 flex justify-between items-center flex-wrap gap-2">
            <h2 className="text-xl font-bold">📡 Precipitation Forecast</h2>
            <div className="flex space-x-1 flex-wrap gap-1">
              {[
                { key: 'current', label: 'Current',  active: 'bg-blue-600',   },
                { key: 'f30',     label: '+30 min',  active: 'bg-green-600',  },
                { key: 'f60',     label: '+60 min',  active: 'bg-yellow-600', },
                { key: 'f90',     label: '+90 min',  active: 'bg-orange-500', },
                { key: 'f180',    label: '+3 hr',    active: 'bg-red-500',    },
                { key: 'f360',    label: '+6 hr',    active: 'bg-red-800',    },
              ].map(({ key, label, active }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                    activeTab === key ? `${active} text-white` : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                >
                  {label}
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
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
                attribution="&copy; OpenStreetMap contributors" 
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
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
                attribution="&copy; OpenStreetMap contributors" 
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
