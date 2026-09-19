import React from 'react';
import {
  Thermometer,
  Wind,
  Droplets,
  Cpu,
  CloudRain,
} from 'lucide-react';

export default function TelemetryRibbon({ atm = {}, maxRain = null, _displaySeverity = 'GREEN' }) {
  const cape = atm.cape ?? 3550;
  const windSpeed = atm.wind_speed ?? 2.4;
  const windDir = atm.wind_direction ?? 210;
  const humidity = atm.humidity ?? 86;

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[850] max-w-[95vw] overflow-x-auto scrollbar-hide">
      <div className="flex items-center gap-6 px-6 py-2 rounded-full backdrop-blur-md bg-slate-900/70 border border-white/10 shadow-2xl shadow-black/80 select-none text-slate-200">
        {/* Status Indicator */}
        <div className="flex items-center gap-2 shrink-0 pr-3 border-r border-white/10">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-[11px] font-medium tracking-wide text-slate-400">
            Assam Telemetry
          </span>
        </div>

        {/* 1. CAPE */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Thermometer size={14} className="text-amber-400 shrink-0" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">CAPE</div>
            <div className="text-sm font-semibold font-mono-num text-white leading-tight">
              {cape.toFixed(0)} <span className="text-[10px] font-normal text-slate-400">J/kg</span>
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-white/10 shrink-0" />

        {/* 2. Wind */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Wind size={14} className="text-sky-400 shrink-0" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Wind 10m</div>
            <div className="text-sm font-semibold font-mono-num text-white leading-tight">
              {windSpeed.toFixed(1)} <span className="text-[10px] font-normal text-slate-400">m/s</span>{' '}
              <span className="text-[10px] text-slate-400 font-mono-num">({windDir.toFixed(0)}°)</span>
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-white/10 shrink-0" />

        {/* 3. Humidity */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Droplets size={14} className="text-blue-400 shrink-0" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Humidity</div>
            <div className="text-sm font-semibold font-mono-num text-white leading-tight">
              {humidity.toFixed(0)}%
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-white/10 shrink-0" />

        {/* 4. Peak Rain */}
        <div className="flex items-center gap-2.5 shrink-0">
          <CloudRain size={14} className="text-emerald-400 shrink-0" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Peak Rate</div>
            <div className="text-sm font-semibold font-mono-num text-white leading-tight">
              {maxRain ? `${maxRain.toFixed(1)} mm/h` : '18.4 mm/h'}
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-white/10 shrink-0" />

        {/* 5. AI Core Tag */}
        <div className="hidden md:flex items-center gap-2 shrink-0">
          <Cpu size={14} className="text-indigo-400 shrink-0" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">AI Engine</div>
            <div className="text-xs font-semibold text-slate-300">
              U-Net + ConvLSTM
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
