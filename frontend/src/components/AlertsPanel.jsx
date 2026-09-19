import React from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  ChevronRight,
  Thermometer,
  Wind,
  Droplets,
  Cpu,
  CheckCircle2,
  Clock,
} from 'lucide-react';

function AlertCard({ alert }) {
  const isRed = alert.severity === 'RED';

  return (
    <div
      className={`p-3 rounded-xl border text-xs flex flex-col gap-1 transition-all ${
        isRed
          ? 'bg-rose-500/10 border-rose-500/20 text-rose-200'
          : 'bg-amber-500/10 border-amber-500/20 text-amber-200'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 font-semibold">
          <AlertTriangle size={13} className={isRed ? 'text-rose-400' : 'text-amber-400'} />
          <span className="text-white">{alert.title}</span>
        </div>
        <span
          className={`px-2 py-0.2 rounded text-[10px] font-mono-num font-semibold uppercase ${
            isRed ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
          }`}
        >
          {alert.severity}
        </span>
      </div>

      {alert.reason && (
        <div className="text-[11px] text-slate-400 leading-snug">
          {alert.reason}
        </div>
      )}

      {alert.eta_minutes && (
        <div className="flex items-center gap-1 text-[10px] font-mono-num text-slate-500 mt-1">
          <Clock size={11} />
          <span>ETA ~{alert.eta_minutes} min</span>
        </div>
      )}
    </div>
  );
}

export default function AlertsPanel({
  alerts = [],
  atm = {},
  rvDisplayTime,
  onClose,
}) {
  const cape = atm.cape ?? 3550;
  const windSpeed = atm.wind_speed ?? 2.4;
  const windDir = atm.wind_direction ?? 210;
  const humidity = atm.humidity ?? 86;

  return (
    <motion.aside
      key="alerts-panel"
      initial={{ x: 30, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 30, opacity: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="fixed top-20 right-6 bottom-20 z-[900] w-80 flex flex-col gap-3.5 p-4 rounded-2xl backdrop-blur-xl bg-slate-900/60 border border-white/5 shadow-2xl shadow-black/60 text-slate-200 select-none hud-scroll overflow-y-auto"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div>
          <div className="text-xs font-semibold text-white tracking-tight">Hazards & Telemetry</div>
          <div className="text-[10px] text-slate-500 font-mono-num">Real-time Parameters</div>
        </div>
        <div className="flex items-center gap-2">
          {alerts.length > 0 ? (
            <span className="px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-400 text-[10px] font-semibold">
              {alerts.length} Active
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-medium border border-emerald-500/20">
              Nominal
            </span>
          )}
          <button
            onClick={onClose}
            title="Close"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>

      {/* ── Real-Time Hazard Alerts Card ── */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[10px] uppercase font-semibold tracking-wider text-slate-400">
          Hazard Monitor
        </label>

        {alerts.length === 0 ? (
          <div className="p-3.5 rounded-xl bg-slate-950/40 border border-white/5 text-center flex flex-col items-center gap-1.5">
            <CheckCircle2 size={20} className="text-emerald-400" />
            <div className="text-xs font-semibold text-slate-200">
              No Active Hazards
            </div>
            <div className="text-[10px] text-slate-500">
              All convective thresholds nominal in Assam domain.
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {alerts.map((a, i) => (
              <AlertCard key={`alert-${i}`} alert={a} />
            ))}
          </div>
        )}
      </div>

      {/* ── Executive-Style Metrics Grid ── */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[10px] uppercase font-semibold tracking-wider text-slate-400">
          Atmospheric Sounding
        </label>

        <div className="grid grid-cols-2 gap-2">
          {/* CAPE */}
          <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold flex items-center justify-between">
              <span>CAPE</span>
              <Thermometer size={12} className="text-amber-400" />
            </div>
            <div className="my-1.5">
              <span className="text-2xl font-semibold font-mono-num text-white">
                {cape.toFixed(0)}
              </span>
              <span className="text-xs text-slate-500 ml-1">J/kg</span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              {cape > 2000 ? 'Extreme instability' : cape > 1000 ? 'Active convection' : 'Stable'}
            </div>
          </div>

          {/* Wind Speed */}
          <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold flex items-center justify-between">
              <span>Wind Speed</span>
              <Wind size={12} className="text-sky-400" />
            </div>
            <div className="my-1.5">
              <span className="text-2xl font-semibold font-mono-num text-white">
                {windSpeed.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500 ml-1">m/s</span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              {windDir.toFixed(0)}° at 10m AGL
            </div>
          </div>

          {/* Relative Humidity */}
          <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold flex items-center justify-between">
              <span>Humidity</span>
              <Droplets size={12} className="text-blue-400" />
            </div>
            <div className="my-1.5">
              <span className="text-2xl font-semibold font-mono-num text-white">
                {humidity.toFixed(0)}
              </span>
              <span className="text-xs text-slate-500 ml-1">%</span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              {humidity >= 80 ? 'High moisture column' : 'Moderate column'}
            </div>
          </div>

          {/* AI Model Tag */}
          <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold flex items-center justify-between">
              <span>Architecture</span>
              <Cpu size={12} className="text-indigo-400" />
            </div>
            <div className="my-1.5">
              <span className="text-sm font-semibold font-mono-num text-white leading-tight">
                Dual AI
              </span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              U-Net + ConvLSTM
            </div>
          </div>
        </div>
      </div>

      {/* ── System Specs Footer ── */}
      <div className="mt-auto p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col gap-1.5 text-xs">
        <div className="flex justify-between items-center text-slate-400">
          <span>Dataset</span>
          <span className="text-slate-300 font-mono-num text-[11px]">PERSIANN 4km Multi-Year</span>
        </div>
        <div className="flex justify-between items-center text-slate-400">
          <span>Terrain</span>
          <span className="text-slate-300 font-mono-num text-[11px]">SRTM 1km DEM</span>
        </div>
        {rvDisplayTime && (
          <div className="flex justify-between items-center text-slate-400 pt-1 border-t border-white/5">
            <span>Radar Sync</span>
            <span className="text-slate-300 font-mono-num text-[11px]">{rvDisplayTime}</span>
          </div>
        )}
      </div>
    </motion.aside>
  );
}
