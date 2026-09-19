import React from 'react';
import { MapPin, X, Droplets, Wind, CloudRain } from 'lucide-react';
import { WMO, wmoEmoji } from '../constants/weather';

export default function LocationWeatherCard({ weather, address, onClose }) {
  if (!weather) return null;
  const emoji = wmoEmoji(weather.weather_code ?? 0);

  return (
    <div className="w-64 p-3.5 rounded-2xl backdrop-blur-xl bg-slate-900/95 border border-cyan-500/40 shadow-2xl shadow-black/90 text-slate-100 select-none relative animate-in fade-in zoom-in-95 duration-200">
      {/* Close button */}
      <button
        onClick={onClose}
        aria-label="Close"
        className="absolute top-2.5 right-2.5 p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
      >
        <X size={14} />
      </button>

      {/* Header */}
      <div className="flex items-center gap-1.5 mb-2 pr-6">
        <MapPin size={14} className="text-cyan-400 shrink-0" />
        <span className="text-xs font-bold font-mono-num text-slate-200 truncate">
          {address ?? 'Your Location'}
        </span>
      </div>

      {/* Main Temp & Condition */}
      <div className="flex items-center gap-3 p-2 rounded-xl bg-slate-950/60 border border-slate-800/70 mb-2.5">
        <span className="text-3xl shrink-0 drop-shadow-md">{emoji}</span>
        <div>
          <div className="text-2xl font-black font-mono-num text-white leading-tight">
            {weather.temperature_2m?.toFixed(1) ?? '--'}
            <span className="text-sm font-normal text-cyan-400 ml-0.5">°C</span>
          </div>
          <div className="text-[11px] text-slate-400 font-medium leading-none">
            {WMO[weather.weather_code] ?? 'Observational Grid'}
          </div>
        </div>
      </div>

      {/* 3-Col Telemetry Grid */}
      <div className="grid grid-cols-3 gap-1.5 mb-2">
        <div className="flex flex-col items-center p-1.5 rounded-lg bg-slate-950/50 border border-slate-800/60 text-center">
          <Droplets size={12} className="text-cyan-400 mb-0.5" />
          <span className="text-[11px] font-mono-num font-bold text-slate-100">
            {weather.relative_humidity_2m?.toFixed(0) ?? '--'}%
          </span>
          <span className="text-[8px] uppercase tracking-wider text-slate-500 font-medium">Humidity</span>
        </div>

        <div className="flex flex-col items-center p-1.5 rounded-lg bg-slate-950/50 border border-slate-800/60 text-center">
          <Wind size={12} className="text-emerald-400 mb-0.5" />
          <span className="text-[11px] font-mono-num font-bold text-slate-100">
            {weather.wind_speed_10m?.toFixed(1) ?? '--'}
          </span>
          <span className="text-[8px] uppercase tracking-wider text-slate-500 font-medium">m/s</span>
        </div>

        <div className="flex flex-col items-center p-1.5 rounded-lg bg-slate-950/50 border border-slate-800/60 text-center">
          <CloudRain size={12} className="text-blue-400 mb-0.5" />
          <span className="text-[11px] font-mono-num font-bold text-slate-100">
            {weather.precipitation?.toFixed(1) ?? '0'}
          </span>
          <span className="text-[8px] uppercase tracking-wider text-slate-500 font-medium">mm</span>
        </div>
      </div>

      {/* Card Footer */}
      <div className="text-[9px] font-mono-num text-slate-400 text-center pt-1 border-t border-slate-800/70">
        Live Atmospheric Sounding · Open-Meteo
      </div>
    </div>
  );
}
