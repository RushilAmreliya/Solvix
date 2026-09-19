import React from 'react';
import { motion } from 'framer-motion';
import {
  Layers,
  Clock,
  Radio,
  ChevronLeft,
  Database,
} from 'lucide-react';
import { TIME_OFFSETS, HAZARD_LAYERS, CONFIDENCE } from '../constants/weather';

export default function Sidebar({
  radarType,
  setRadarType,
  timeOffset,
  setTimeOffset,
  setActiveLayer,
  data,
  rvDisplayTime,
  onClose,
}) {
  // Determine active slider step (0 to 5)
  const currentStep = TIME_OFFSETS.findIndex((t) => t.key === timeOffset);
  const activeTimeObj = TIME_OFFSETS[currentStep >= 0 ? currentStep : 0];

  const handleSliderChange = (e) => {
    const idx = parseInt(e.target.value, 10);
    const targetTime = TIME_OFFSETS[idx]?.key ?? 'current';
    setTimeOffset(targetTime);
    setRadarType('precipitation');
    setActiveLayer(targetTime);
  };

  const handleTypeSelect = (typeKey) => {
    setRadarType(typeKey);
    if (typeKey === 'precipitation') {
      setActiveLayer(timeOffset);
    } else {
      setActiveLayer(typeKey);
    }
  };

  const handleTimeSelect = (timeKey) => {
    setTimeOffset(timeKey);
    setRadarType('precipitation');
    setActiveLayer(timeKey);
  };

  return (
    <motion.aside
      key="sidebar-panel"
      initial={{ x: -60, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -60, opacity: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className="fixed top-20 left-4 bottom-16 z-[900] w-80 flex flex-col gap-3 p-3.5 rounded-2xl backdrop-blur-xl bg-slate-900/85 border border-slate-800/70 shadow-2xl shadow-black/80 text-slate-200 select-none hud-scroll overflow-y-auto"
    >
      {/* ── Panel Header with Collapse Action ── */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/70">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#00B0FF]" />
          <span className="font-extrabold text-xs tracking-wider uppercase text-slate-100 font-mono-num">
            Radar & Convective Control
          </span>
        </div>
        <button
          onClick={onClose}
          title="Collapse Panel"
          className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
        >
          <ChevronLeft size={16} />
        </button>
      </div>

      {/* ── Segmented Control: Radar & Hazard Types ── */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-[10px] font-bold tracking-wider uppercase text-slate-400">
          <span className="flex items-center gap-1.5">
            <Layers size={12} className="text-cyan-400" />
            Radar Product
          </span>
          <span className="text-slate-500 font-mono-num">5 Modes</span>
        </div>

        <div className="grid grid-cols-1 gap-1">
          {/* Precipitation Master Tab */}
          <button
            onClick={() => handleTypeSelect('precipitation')}
            className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold border transition-all duration-150 ${
              radarType === 'precipitation'
                ? 'bg-cyan-500/15 border-cyan-500/60 text-cyan-300 shadow-[0_0_12px_rgba(0,176,255,0.2)]'
                : 'bg-slate-950/40 border-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  radarType === 'precipitation' ? 'bg-cyan-400' : 'bg-slate-600'
                }`}
              />
              <span>Precipitation (IMD Z-R)</span>
            </div>
            <span className="text-[10px] font-mono-num px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
              {activeTimeObj.label}
            </span>
          </button>

          {/* Convective Hazards Sub-grid */}
          <div className="grid grid-cols-2 gap-1 mt-0.5">
            {HAZARD_LAYERS.map(({ key, label, icon: Icon, color }) => {
              const isSelected = radarType === key;
              return (
                <button
                  key={key}
                  onClick={() => handleTypeSelect(key)}
                  className={`flex items-center gap-2 px-2.5 py-2 rounded-xl text-[11px] font-semibold border transition-all duration-150 text-left ${
                    isSelected
                      ? 'shadow-[0_0_12px_rgba(0,0,0,0.5)]'
                      : 'bg-slate-950/40 border-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  style={
                    isSelected
                      ? {
                          backgroundColor: `${color}18`,
                          borderColor: `${color}70`,
                          color: color,
                          boxShadow: `0 0 10px ${color}30`,
                        }
                      : {}
                  }
                >
                  <Icon size={13} style={{ color: isSelected ? color : '#64748b' }} className="shrink-0" />
                  <span className="truncate">{label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Time Offset Slider & Segmented Selector ── */}
      <div className="flex flex-col gap-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/70">
        <div className="flex items-center justify-between text-[10px] font-bold tracking-wider uppercase text-slate-400">
          <span className="flex items-center gap-1.5">
            <Clock size={12} className="text-emerald-400" />
            Time Offset Selector
          </span>
          <span className="text-emerald-400 font-mono-num font-bold">
            {activeTimeObj.label} ({activeTimeObj.sublabel})
          </span>
        </div>

        {/* Range Slider Track */}
        <div className="px-1 pt-1">
          <input
            type="range"
            min="0"
            max="5"
            step="1"
            value={currentStep >= 0 ? currentStep : 0}
            onChange={handleSliderChange}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
        </div>

        {/* Segmented Button Row */}
        <div className="grid grid-cols-6 gap-1 text-center">
          {TIME_OFFSETS.map((t) => {
            const isSel = radarType === 'precipitation' && timeOffset === t.key;
            return (
              <button
                key={t.key}
                onClick={() => handleTimeSelect(t.key)}
                className={`py-1.5 rounded-lg text-[10px] font-mono-num font-bold border transition-all ${
                  isSel
                    ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_8px_rgba(0,176,255,0.3)]'
                    : 'bg-slate-900/60 border-slate-800/60 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="text-[10px] text-slate-400 font-mono-num leading-tight mt-0.5 px-1">
          {CONFIDENCE[timeOffset] ?? 'Operational forecast sequence'}
        </div>
      </div>

      {/* ── IMD Rain Rate Color Legend Scale Gauge ── */}
      <div className="flex flex-col gap-1.5 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/70">
        <div className="flex items-center justify-between text-[10px] font-bold tracking-wider uppercase text-slate-400">
          <span>IMD Rain Rate Scale</span>
          <span className="text-cyan-400 font-mono-num">mm/hr · dBZ</span>
        </div>

        {/* Continuous Color Scale Bar */}
        <div
          className="h-2.5 w-full rounded-md shadow-inner"
          style={{
            background:
              'linear-gradient(to right, #000080 0%, #0000ff 20%, #00ffff 40%, #00ff00 60%, #ffff00 75%, #ff7f00 90%, #ff0000 100%)',
          }}
        />

        {/* Gauge Ticks & Readouts */}
        <div className="flex justify-between text-[9px] font-mono-num text-slate-400 font-medium px-0.5">
          <div>
            <div className="text-slate-300 font-bold">0</div>
            <div className="text-[8px] text-slate-400">15dBZ</div>
          </div>
          <div>
            <div className="text-slate-300 font-bold">5</div>
            <div className="text-[8px] text-slate-400">30dBZ</div>
          </div>
          <div>
            <div className="text-slate-300 font-bold">15</div>
            <div className="text-[8px] text-slate-400">42dBZ</div>
          </div>
          <div>
            <div className="text-slate-300 font-bold">35</div>
            <div className="text-[8px] text-slate-400">52dBZ</div>
          </div>
          <div className="text-right">
            <div className="text-red-400 font-bold">60+</div>
            <div className="text-[8px] text-red-400">Cloudburst</div>
          </div>
        </div>
      </div>

      {/* ── In-Memory Frame Buffer Status Card ── */}
      <div className="mt-auto p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400">
            <Database size={12} className="text-emerald-400" />
            <span>{data?.source === 'live-radar' ? 'Live Radar Buffer' : 'Frame Buffer'}</span>
          </div>
          <span
            className={`px-1.5 py-0.5 rounded text-[9px] font-mono-num font-bold ${
              data?.source === 'live-radar'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                : 'bg-slate-900 text-slate-400 border border-slate-800'
            }`}
          >
            {data?.source === 'live-radar' ? 'REAL DWR' : 'SIMULATION'}
          </span>
        </div>

        <div className="flex items-baseline justify-between mb-1">
          <span className="text-2xl font-black font-mono-num text-white">
            {data?.buffer_size ?? 0}
            <span className="text-xs font-normal text-slate-400 ml-1">/ 20</span>
          </span>
          <span className="text-[10px] font-mono-num text-slate-400">
            {data?.source === 'live-radar' ? 'IMD Sweeps Active' : 'Sequential Frames'}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(100, ((data?.buffer_size ?? 0) / 20) * 100)}%`,
              background:
                data?.source === 'live-radar'
                  ? 'linear-gradient(to right, #00E676, #00B0FF)'
                  : 'linear-gradient(to right, #3b82f6, #00B0FF)',
            }}
          />
        </div>

        {/* Radar Timestamp info */}
        {rvDisplayTime && (
          <div className="flex items-center gap-1.5 mt-2.5 pt-2 border-t border-slate-800/60 text-[10px] font-mono-num text-slate-400">
            <Radio size={11} className="text-emerald-400 animate-pulse" />
            <span>Sweep Time: {rvDisplayTime}</span>
          </div>
        )}
      </div>
    </motion.aside>
  );
}
