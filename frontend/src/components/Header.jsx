import React from 'react';
import {
  CloudRain,
  Radio,
  LocateFixed,
  RefreshCcw,
  Bell,
  SlidersHorizontal,
} from 'lucide-react';

export default function Header({
  displaySeverity,
  syncingRadar,
  syncLiveRadar,
  locating,
  locateUser,
  _connectionMode,
  _data,
  _lastUpdated,
  onRefresh,
  alertCount = 0,
  basemapStyle,
  setBasemapStyle,
  leftOpen,
  setLeftOpen,
  _rightOpen,
  setRightOpen,
}) {
  const isClear = displaySeverity === 'GREEN';

  return (
    <header className="w-full h-14 flex items-center justify-between px-4 sm:px-6 rounded-2xl backdrop-blur-xl bg-slate-900/60 border border-white/5 shadow-2xl shadow-black/60 text-slate-100 select-none">
      {/* ── Left: Logo & Status Badge ── */}
      <div className="flex items-center gap-3.5">
        {/* Toggle Controls Drawer */}
        <button
          onClick={() => setLeftOpen((prev) => !prev)}
          title={leftOpen ? 'Hide controls' : 'Show controls'}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-xs font-medium transition-all ${
            leftOpen
              ? 'bg-white/10 border-white/15 text-white shadow-sm'
              : 'bg-transparent border-white/5 text-slate-400 hover:text-white hover:border-white/10'
          }`}
        >
          <SlidersHorizontal size={14} />
          <span className="hidden sm:inline">Controls</span>
        </button>

        {/* Brand Mark & Title */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-b from-blue-500/20 to-indigo-500/10 border border-white/10 text-sky-400">
            <CloudRain size={17} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-semibold text-sm tracking-tight text-white">
              NowCast Fusion
            </span>
            <span className="text-[11px] text-slate-500 hidden md:inline">
              Assam EWS
            </span>
          </div>
        </div>

        {/* Minimal Status Badge */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-all ${
            isClear
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isClear ? 'bg-emerald-400' : 'bg-rose-400 animate-pulse'
            }`}
          />
          <span className="text-[11px]">
            {isClear ? 'All Clear' : `${displaySeverity} Alert`}
          </span>
        </div>
      </div>

      {/* ── Center: Pipeline Minimal Tag ── */}
      <div className="hidden xl:flex items-center gap-2 text-xs text-slate-400 font-mono-num">
        <span className="text-slate-500">Pipeline:</span>
        <span className="text-slate-300">PySTEPS · U-Net · ConvLSTM</span>
        <span className="text-slate-600">/</span>
        <span className="text-slate-400">4km Domain</span>
      </div>

      {/* ── Right: Clean Outline Actions ── */}
      <div className="flex items-center gap-2 sm:gap-2.5">
        {/* Sync Live Radar Button */}
        <button
          onClick={syncLiveRadar}
          disabled={syncingRadar}
          title="Fetch latest radar sweep"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-xs font-medium text-slate-200 transition-all disabled:opacity-50"
        >
          <Radio size={13} className={syncingRadar ? 'animate-spin text-sky-400' : 'text-slate-400'} />
          <span className="hidden sm:inline">
            {syncingRadar ? 'Syncing...' : 'Sync Radar'}
          </span>
        </button>

        {/* My Location Button */}
        <button
          onClick={locateUser}
          disabled={locating}
          title="Locate me"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-xs font-medium text-slate-200 transition-all disabled:opacity-50"
        >
          <LocateFixed size={13} className={locating ? 'animate-spin text-sky-400' : 'text-slate-400'} />
          <span className="hidden sm:inline">
            {locating ? 'Locating...' : 'My Location'}
          </span>
        </button>

        {/* Basemap Toggle */}
        {setBasemapStyle && (
          <div className="hidden sm:flex items-center p-0.5 rounded-xl border border-white/10 bg-black/20">
            <button
              onClick={() => setBasemapStyle('satellite')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                basemapStyle === 'satellite'
                  ? 'bg-white/15 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sat
            </button>
            <button
              onClick={() => setBasemapStyle('streets')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                basemapStyle === 'streets'
                  ? 'bg-white/15 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Dark
            </button>
          </div>
        )}

        {/* Hazard Alert Notification Bell */}
        <button
          onClick={() => setRightOpen((prev) => !prev)}
          title={alertCount > 0 ? `${alertCount} active alerts` : 'No active alerts'}
          className={`relative p-2 rounded-xl border transition-all ${
            alertCount > 0
              ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              : 'border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-slate-400 hover:text-white'
          }`}
        >
          <Bell size={14} />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[9px] font-bold text-white font-mono-num">
              {alertCount}
            </span>
          )}
        </button>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          title="Refresh forecast data"
          className="p-2 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-slate-400 hover:text-white transition-all"
        >
          <RefreshCcw size={14} />
        </button>
      </div>
    </header>
  );
}
