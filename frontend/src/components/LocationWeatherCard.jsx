import React from 'react';
import { MapPin, X, Droplets, Wind, CloudRain } from 'lucide-react';
import { WMO, wmoEmoji } from '../constants/weather';

export default function LocationWeatherCard({ weather, address, onClose }) {
  if (!weather) return null;
  const emoji = wmoEmoji(weather.weather_code ?? 0);

  return (
    <div className="loc-card">
      <button className="loc-card-close" onClick={onClose} aria-label="Close">
        <X size={13} />
      </button>
      <div className="loc-card-header">
        <MapPin size={14} color="#60a5fa" />
        <span className="loc-card-place">{address ?? 'Your Location'}</span>
      </div>
      <div className="loc-card-main">
        <span className="loc-emoji">{emoji}</span>
        <div>
          <div className="loc-temp">{weather.temperature_2m?.toFixed(1) ?? '--'}°C</div>
          <div className="loc-condition">{WMO[weather.weather_code] ?? 'Unknown'}</div>
        </div>
      </div>
      <div className="loc-grid">
        <div className="loc-stat">
          <Droplets size={11} color="#38bdf8" />
          <span>{weather.relative_humidity_2m?.toFixed(0) ?? '--'}%</span>
          <span className="loc-stat-label">Humidity</span>
        </div>
        <div className="loc-stat">
          <Wind size={11} color="#94a3b8" />
          <span>{weather.wind_speed_10m?.toFixed(1) ?? '--'} m/s</span>
          <span className="loc-stat-label">Wind</span>
        </div>
        <div className="loc-stat">
          <CloudRain size={11} color="#60a5fa" />
          <span>{weather.precipitation?.toFixed(1) ?? '0'} mm</span>
          <span className="loc-stat-label">Precip</span>
        </div>
      </div>
      <div className="loc-footer">Live data · Open-Meteo · No API key required</div>
    </div>
  );
}
