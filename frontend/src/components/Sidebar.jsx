import React from 'react';
import { motion } from 'framer-motion';
import {
  Clock,
  Radio,
  ChevronLeft,
  Database,
  CloudRain,
  CloudSnow,
  Zap,
  Wind,
} from 'lucide-react';
import { TIME_OFFSETS, CONFIDENCE } from '../constants/weather';

const PRODUCT_TABS = [
  { key: 'precipitation', label: 'Precipitation', icon: CloudRain },
  { key: 'cloudburst', label: 'Cloudburst', icon: CloudRain, color: '#f43f5e' },
  { key: 'lightning', label: 'Lightning', icon: Zap, color: '#f59e0b' },
  { key: 'hail', label: 'Hail', icon: CloudSnow, color: '#38bdf8' },
  { key: 'downburst', label: 'Downburst', icon: Wind, color: '#a855f7' },
];

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
      initial={{ x: -30, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -30, opacity: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="fixed top-20 left-6 bottom-20 z-[900] w-80 flex flex-col gap-3.5 p-4 rounded-2xl backdrop-blur-xl bg-slate-900/60 border border-white/5 shadow-2xl shadow-black/60 text-slate-200 select-none hud-scroll overflow-y-auto"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div>
          <div className="text-xs font-semibold text-white tracking-tight">Radar & Controls</div>
          <div className="text-[10px] text-slate-500 font-mono-num">Assam Convective Grid</div>
        </div>
        <button
          onClick={onClose}
          title="Close"
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          <ChevronLeft size={15} />
        </button>
      </div>

      {/* ── Shadcn/UI Style Segmented Control for Radar Products ── */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[10px] uppercase font-semibold tracking-wider text-slate-400">
          Layer Product
        </label>
        <div className="p-1 rounded-xl bg-slate-950/50 border border-white/5 grid grid-cols-1 gap-1">
          {/* Main Precipitation Tab */}
          <button
            onClick={() => handleTypeSelect('precipitation')}
            className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              radarType === 'precipitation'
                ? 'bg-white/10 text-white shadow-sm font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
            }`}
          >
            <div className="flex items-center gap-2">
              <CloudRain size={14} className={radarType === 'precipitation' ? 'text-sky-400' : 'text-slate-500'} />
              <span>Precipitation</span>
            </div>
            <span className="text-[10px] font-mono-num text-slate-400">
              {activeTimeObj.label}
            </span>
          </button>

          {/* Hazard Sub-row */}
          <div className="grid grid-cols-2 gap-1 pt-0.5">
            {PRODUCT_TABS.slice(1).map(({ key, label, icon: Icon, color }) => {
              const isSel = radarType === key;
              return (
                <button
                  key={key}
                  onClick={() => handleTypeSelect(key)}
                  className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-all ${
                    isSel
                      ? 'bg-white/10 text-white shadow-sm font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
                  }`}
                >
                  <Icon size={13} style={{ color: isSel ? color : '#64748b' }} />
                  <span className="truncate">{label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Time Offset Selector ── */}
      <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col gap-2">
        <div className="flex items-center justify-between text-[10px] uppercase font-semibold tracking-wider text-slate-400">
          <div className="flex items-center gap-1.5">
            <Clock size={12} className="text-sky-400" />
            <span>Time Forecast</span>
          </div>
          <span className="text-white font-mono-num font-semibold lowercase">
            {activeTimeObj.label}
          </span>
        </div>

        {/* Minimal Slider */}
        <input
          type="range"
          min="0"
          max="5"
          step="1"
          value={currentStep >= 0 ? currentStep : 0}
          onChange={handleSliderChange}
          className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400"
        />

        {/* Segmented Button Row */}
        <div className="grid grid-cols-6 gap-1 text-center">
          {TIME_OFFSETS.map((t) => {
            const isSel = radarType === 'precipitation' && timeOffset === t.key;
            return (
              <button
                key={t.key}
                onClick={() => handleTimeSelect(t.key)}
                className={`py-1 rounded-md text-[10px] font-mono-num font-medium transition-all ${
                  isSel
                    ? 'bg-white/15 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="text-[10px] text-slate-500 font-mono-num leading-tight pt-1 border-t border-white/5">
          {CONFIDENCE[timeOffset] ?? 'Nowcast sequence'}
        </div>
      </div>

      {/* ── Minimal IMD Rain Rate Legend ── */}
      <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-[10px] uppercase font-semibold tracking-wider text-slate-400">
          <span>IMD Rain Scale</span>
          <span className="text-slate-500 font-mono-num">mm/hr</span>
        </div>
        <div
          className="h-1.5 w-full rounded-full"
          style={{
            background:
              'linear-gradient(to right, #000080, #0000ff, #00ffff, #00ff00, #ffff00, #ff7f00, #ff0000)',
          }}
        />
        <div className="flex justify-between text-[9px] font-mono-num text-slate-500 pt-0.5">
          <span>0 (Light)</span>
          <span>15</span>
          <span>35</span>
          <span className="text-rose-400">60+ (Cloudburst)</span>
        </div>
      </div>

      {/* ── Frame Buffer & Diagnostics (Executive Style) ── */}
      <div className="mt-auto p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col gap-2 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-slate-400 font-medium">
            <Database size={13} className="text-slate-500" />
            <span>Radar Cache</span>
          </div>
          <span className="text-xs font-mono-num font-semibold text-white">
            {data?.buffer_size ?? 0} <span className="text-slate-500 text-[10px]">/ 20</span>
          </span>
        </div>

        <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-sky-500 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, ((data?.buffer_size ?? 0) / 20) * 100)}%` }}
          />
        </div>

        {rvDisplayTime && (
          <div className="flex items-center gap-1.5 text-[10px] font-mono-num text-slate-500 pt-1 border-t border-white/5">
            <Radio size={11} className="text-emerald-400" />
            <span>Latest Sweep: {rvDisplayTime}</span>
          </div>
        )}
      </div>
    </motion.aside>
  );
}
