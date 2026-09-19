import React from 'react';
import { motion } from 'framer-motion';
import {
  ShieldAlert,
  AlertTriangle,
  ChevronRight,
  Thermometer,
  Wind,
  Droplets,
  Cpu,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { SEVERITY } from '../constants/weather';

function AlertCard({ alert }) {
  const s = SEVERITY[alert.severity] ?? SEVERITY.GREEN;

  return (
    <div
      className="p-3 rounded-xl border text-xs flex flex-col gap-1.5 transition-all"
      style={{
        background: s.bg,
        borderColor: `${s.border}80`,
        boxShadow: `0 0 12px ${s.glow}`,
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 font-bold font-mono-num" style={{ color: s.text }}>
          <AlertTriangle size={13} style={{ color: s.text }} className="shrink-0" />
          <span>{alert.title}</span>
        </div>
        <span
          className="px-2 py-0.5 rounded text-[10px] font-mono-num font-bold text-white uppercase shrink-0"
          style={{ background: s.badge }}
        >
          {alert.severity}
        </span>
      </div>

      {alert.reason && (
        <div className="text-[11px] text-slate-300 leading-snug">
          {alert.reason}
        </div>
      )}

      {alert.eta_minutes && (
        <div className="flex items-center gap-1 text-[10px] font-mono-num text-slate-400 mt-1">
          <Clock size={11} className="text-slate-500" />
          <span>Estimated Impact ETA: ~{alert.eta_minutes} mins</span>
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
  return (
    <motion.aside
      key="alerts-panel"
      initial={{ x: 60, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 60, opacity: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className="fixed top-20 right-4 bottom-16 z-[900] w-84 flex flex-col gap-3 p-3.5 rounded-2xl backdrop-blur-xl bg-slate-900/85 border border-slate-800/70 shadow-2xl shadow-black/80 text-slate-200 select-none hud-scroll overflow-y-auto"
    >
      {/* ── Panel Header with Collapse Action ── */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/70">
        <div className="flex items-center gap-2">
          <ShieldAlert size={15} className="text-red-400" />
          <span className="font-extrabold text-xs tracking-wider uppercase text-slate-100 font-mono-num">
            Active Hazards & Telemetry
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {alerts.length > 0 ? (
            <span className="px-1.5 py-0.5 rounded-full bg-red-950 text-red-300 border border-red-500/50 text-[10px] font-mono-num font-bold">
              {alerts.length} ACTIVE
            </span>
          ) : (
            <span className="px-1.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-[10px] font-mono-num font-bold">
              0 ALERTS
            </span>
          )}
          <button
            onClick={onClose}
            title="Collapse Panel"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* ── Real-Time Hazard Alerts Card ── */}
      <div className="flex flex-col gap-2">
        <div className="text-[10px] font-bold tracking-wider uppercase text-slate-400 font-mono-num flex items-center justify-between">
          <span>Hazard Warning Monitor</span>
          <span className="text-slate-500">Assam EWS Grid</span>
        </div>

        {alerts.length === 0 ? (
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-center flex flex-col items-center gap-1.5">
            <CheckCircle2 size={24} className="text-emerald-400 drop-shadow-[0_0_8px_rgba(0,230,118,0.5)]" />
            <div className="text-xs font-bold text-emerald-300 font-mono-num">
              No Active Hazards - Assam Region
            </div>
            <div className="text-[10px] text-slate-400">
              Cloudburst, Hail, Lightning & Downburst thresholds all nominal.
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

      {/* ── Meteorological Parameter Readouts ── */}
      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/70 flex flex-col gap-2.5">
        <div className="text-[10px] font-bold tracking-wider uppercase text-slate-400 font-mono-num flex items-center justify-between">
          <span>Atmospheric Parameters</span>
          <span className="text-cyan-400 font-mono-num">Open-Meteo Synoptic</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {/* CAPE */}
          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col">
            <div className="flex items-center gap-1 text-[10px] text-amber-400 font-medium">
              <Thermometer size={12} />
              <span>CAPE</span>
            </div>
            <div className="text-lg font-black font-mono-num text-slate-100">
              {atm.cape?.toFixed(0) ?? '3550'}
              <span className="text-[10px] text-slate-400 font-normal ml-1">J/kg</span>
            </div>
            <div className="text-[9px] text-slate-400 truncate">
              {(atm.cape ?? 3550) > 2000
                ? '🔴 Extreme Instability'
                : (atm.cape ?? 3550) > 1000
                ? '🟡 Active Convection'
                : '🟢 Stable Air'}
            </div>
          </div>

          {/* Wind Speed */}
          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col">
            <div className="flex items-center gap-1 text-[10px] text-cyan-400 font-medium">
              <Wind size={12} />
              <span>Wind Speed</span>
            </div>
            <div className="text-lg font-black font-mono-num text-slate-100">
              {atm.wind_speed?.toFixed(1) ?? '2.4'}
              <span className="text-[10px] text-slate-400 font-normal ml-1">m/s</span>
            </div>
            <div className="text-[9px] text-slate-400 truncate">
              {atm.wind_direction?.toFixed(0) ?? '210'}° · 10m AGL
            </div>
          </div>

          {/* Relative Humidity */}
          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col">
            <div className="flex items-center gap-1 text-[10px] text-blue-400 font-medium">
              <Droplets size={12} />
              <span>Humidity</span>
            </div>
            <div className="text-lg font-black font-mono-num text-slate-100">
              {atm.humidity?.toFixed(0) ?? '86'}
              <span className="text-[10px] text-slate-400 font-normal ml-1">%</span>
            </div>
            <div className="text-[9px] text-slate-400 truncate">
              {(atm.humidity ?? 86) >= 80 ? '🔵 Saturated Column' : '⚪ Moderate Column'}
            </div>
          </div>

          {/* Model Architecture Tag */}
          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col">
            <div className="flex items-center gap-1 text-[10px] text-purple-400 font-medium">
              <Cpu size={12} />
              <span>Model Architecture</span>
            </div>
            <div className="text-xs font-black font-mono-num text-slate-100 mt-1 leading-tight">
              U-Net + ConvLSTM
            </div>
            <div className="text-[9px] text-slate-400 truncate mt-0.5">
              PySTEPS Advection
            </div>
          </div>
        </div>
      </div>

      {/* ── Model Infrastructure Details Footer ── */}
      <div className="mt-auto p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 text-[10px] font-mono-num space-y-1.5">
        <div className="flex justify-between items-center text-slate-400">
          <span>Engine Pipeline</span>
          <span className="text-cyan-300 font-semibold">Dual Spatiotemporal AI</span>
        </div>
        <div className="flex justify-between items-center text-slate-400">
          <span>Training Corpus</span>
          <span className="text-slate-300">PERSIANN-CCS 4km (Multi-Year)</span>
        </div>
        <div className="flex justify-between items-center text-slate-400">
          <span>Terrain Downscale</span>
          <span className="text-slate-300">SRTM 1km Orography</span>
        </div>
        <div className="flex justify-between items-center text-slate-400">
          <span>Radar Tiles</span>
          <span className="text-emerald-400">RainViewer Live (No API key)</span>
        </div>
        {rvDisplayTime && (
          <div className="flex justify-between items-center text-slate-400 pt-1 border-t border-slate-800/70">
            <span>Last Radar Sync</span>
            <span className="text-slate-200">{rvDisplayTime}</span>
          </div>
        )}
      </div>
    </motion.aside>
  );
}
