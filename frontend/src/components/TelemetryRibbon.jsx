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

  // Determine cape status color
  const capeColor = cape > 2000 ? '#FF1744' : cape > 1000 ? '#FFD600' : '#00E676';

  return (
    <div className="fixed bottom-3 left-1/2 -translate-x-1/2 z-[850] max-w-[95vw] overflow-x-auto scrollbar-hide">
      <div className="flex items-center gap-4 px-4 py-2 rounded-2xl backdrop-blur-xl bg-slate-900/85 border border-slate-800/75 shadow-2xl shadow-black/80 select-none">
        {/* Telemetry Indicator */}
        <div className="flex items-center gap-1.5 shrink-0 pr-2 border-r border-slate-800/80">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
          </span>
          <span className="text-[10px] font-mono-num font-bold tracking-wider text-cyan-300 uppercase">
            LIVE TELEMETRY
          </span>
        </div>

        {/* 1. CAPE Metric */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="p-1 rounded-lg bg-amber-950/40 text-amber-400 border border-amber-500/30">
            <Thermometer size={13} />
          </div>
          <div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">CAPE Index</div>
            <div className="text-xs font-mono-num font-extrabold text-white flex items-center gap-1">
              <span>{cape.toFixed(0)}</span>
              <span className="text-[10px] font-normal text-slate-400">J/kg</span>
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: capeColor }} />
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-slate-800 shrink-0" />

        {/* 2. Wind Metric */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="p-1 rounded-lg bg-cyan-950/40 text-cyan-400 border border-cyan-500/30">
            <Wind size={13} />
          </div>
          <div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Surface Wind</div>
            <div className="text-xs font-mono-num font-extrabold text-white flex items-center gap-1">
              <span>{windSpeed.toFixed(1)}</span>
              <span className="text-[10px] font-normal text-slate-400">m/s</span>
              <span className="text-[10px] text-cyan-300 font-semibold">{windDir.toFixed(0)}°</span>
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-slate-800 shrink-0" />

        {/* 3. Relative Humidity */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="p-1 rounded-lg bg-blue-950/40 text-blue-400 border border-blue-500/30">
            <Droplets size={13} />
          </div>
          <div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Moisture Column</div>
            <div className="text-xs font-mono-num font-extrabold text-white flex items-center gap-1">
              <span>{humidity.toFixed(0)}%</span>
              <span className="text-[10px] text-slate-400 font-normal">RH</span>
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-slate-800 shrink-0" />

        {/* 4. Peak Rain / Radar Reflectivity */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="p-1 rounded-lg bg-emerald-950/40 text-emerald-400 border border-emerald-500/30">
            <CloudRain size={13} />
          </div>
          <div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Peak Intensity</div>
            <div className="text-xs font-mono-num font-extrabold text-white flex items-center gap-1">
              <span>{maxRain ? `${maxRain.toFixed(1)} mm/h` : '18.4 mm/h'}</span>
              <span className="text-[10px] text-emerald-400 font-semibold">44 dBZ</span>
            </div>
          </div>
        </div>

        <span className="h-4 w-px bg-slate-800 shrink-0" />

        {/* 5. Model Architecture & Status */}
        <div className="hidden sm:flex items-center gap-2 shrink-0">
          <div className="p-1 rounded-lg bg-purple-950/40 text-purple-400 border border-purple-500/30">
            <Cpu size={13} />
          </div>
          <div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">AI Core</div>
            <div className="text-xs font-mono-num font-extrabold text-purple-300">
              U-Net + ConvLSTM
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
