import React from 'react';
import {
  CloudRain,
  Radio,
  LocateFixed,
  Wifi,
  WifiOff,
  Activity,
  Clock,
  RefreshCcw,
  Bell,
  Sliders,
} from 'lucide-react';
import { SEVERITY } from '../constants/weather';

export default function Header({
  displaySeverity,
  syncingRadar,
  syncLiveRadar,
  locating,
  locateUser,
  connectionMode,
  data,
  lastUpdated,
  onRefresh,
  alertCount = 0,
  basemapStyle,
  setBasemapStyle,
  leftOpen,
  setLeftOpen,
  _rightOpen,
  setRightOpen,
}) {
  const worstStyle = SEVERITY[displaySeverity] ?? SEVERITY.GREEN;

  const connStatus = {
    ws:         { Icon: Wifi,     label: 'LIVE WS',       color: '#00E676' },
    http:       { Icon: Radio,    label: 'POLL 30s',      color: '#FFD600' },
    error:      { Icon: WifiOff,  label: 'OFFLINE',       color: '#FF1744' },
    connecting: { Icon: Activity, label: 'CONNECTING...', color: '#00B0FF' },
  }[connectionMode] ?? { Icon: Activity, label: connectionMode, color: '#94a3b8' };
  const ConnIcon = connStatus.Icon;

  return (
    <header className="w-full flex items-center justify-between gap-3 px-4 py-2.5 rounded-2xl backdrop-blur-xl bg-slate-900/80 border border-slate-800/70 shadow-2xl shadow-black/80 text-slate-100 select-none">
      {/* ── Left: Logo & Live Status Badge ── */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Sidebar Toggle Button (HUD) */}
        <button
          onClick={() => setLeftOpen((prev) => !prev)}
          title={leftOpen ? 'Collapse Radar Controls' : 'Expand Radar Controls'}
          className={`p-1.5 rounded-lg border transition-all duration-200 ${
            leftOpen
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 shadow-[0_0_10px_rgba(0,176,255,0.2)]'
              : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <Sliders size={16} />
        </button>

        {/* Brand Logo & Subtitle */}
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-950/80 to-blue-900/60 border border-cyan-500/40 shadow-[0_0_15px_rgba(0,176,255,0.25)]">
            <CloudRain size={20} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(0,176,255,0.8)]" />
            <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
          </div>
          <div className="leading-tight">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-sm tracking-tight text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.2)]">
                NowCast Fusion
              </span>
              <span className="px-1.5 py-0.5 text-[9px] font-bold tracking-wider uppercase rounded bg-cyan-950/90 text-cyan-300 border border-cyan-500/30">
                v2.4 HUD
              </span>
            </div>
            <div className="text-[10px] text-slate-400 tracking-wide font-medium">
              Convective EWS · North-East India (Assam)
            </div>
          </div>
        </div>

        {/* Live Pulsing Status Badge */}
        <div
          className="flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-bold tracking-wider transition-all duration-300"
          style={{
            background: worstStyle.bg,
            borderColor: worstStyle.border,
            boxShadow: `0 0 16px ${worstStyle.glow}`,
          }}
        >
          <span className="relative flex h-2.5 w-2.5">
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{ background: worstStyle.border }}
            />
            <span
              className="relative inline-flex rounded-full h-2.5 w-2.5"
              style={{ background: worstStyle.border }}
            />
          </span>
          <span style={{ color: worstStyle.text }} className="font-mono-num font-bold text-[11px]">
            {displaySeverity === 'GREEN' ? 'ALL CLEAR' : `${displaySeverity} ALERT`}
          </span>
        </div>
      </div>

      {/* ── Center: Radar / Model Sync Pill ── */}
      <div className="hidden lg:flex items-center gap-3 px-3 py-1 rounded-xl bg-slate-950/60 border border-slate-800/70 text-xs">
        <div className="flex items-center gap-1.5 text-slate-400">
          <Activity size={13} className="text-cyan-400" />
          <span className="text-[11px] font-medium text-slate-300">PySTEPS + U-Net + ConvLSTM</span>
        </div>
        <span className="h-3 w-px bg-slate-800" />
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono-num">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>4km Domain</span>
        </div>
      </div>

      {/* ── Right: HUD Quick Actions ── */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Sync Live Radar Button */}
        <button
          onClick={syncLiveRadar}
          disabled={syncingRadar}
          title="Fetch & ingest real-time radar sweep from IMD / RainViewer"
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] font-semibold tracking-tight transition-all duration-200 ${
            syncingRadar
              ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-300 animate-pulse'
              : 'bg-emerald-950/40 hover:bg-emerald-900/50 border-emerald-500/40 text-emerald-300 hover:border-emerald-400 shadow-[0_0_12px_rgba(0,230,118,0.15)]'
          }`}
        >
          <Radio size={13} className={syncingRadar ? 'animate-spin text-emerald-400' : 'text-emerald-400'} />
          <span className="hidden sm:inline">
            {syncingRadar ? 'Ingesting Sweep...' : 'Sync Live Radar'}
          </span>
        </button>

        {/* My Location Geolocation Button */}
        <button
          onClick={locateUser}
          disabled={locating}
          title="Geolocate user & fetch local convective risk"
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] font-semibold tracking-tight transition-all duration-200 ${
            locating
              ? 'bg-cyan-950/60 border-cyan-500/50 text-cyan-300 animate-pulse'
              : 'bg-cyan-950/30 hover:bg-cyan-900/40 border-cyan-500/30 text-cyan-300 hover:border-cyan-400'
          }`}
        >
          <LocateFixed size={13} className={locating ? 'animate-spin text-cyan-400' : 'text-cyan-400'} />
          <span className="hidden sm:inline">{locating ? 'Locating...' : 'My Location'}</span>
        </button>

        {/* Live Radar Feed Status Tag */}
        <div
          className={`flex items-center gap-1.5 px-2 py-1 rounded-xl border text-[10px] font-mono-num font-bold tracking-wider uppercase ${
            data?.is_live_radar
              ? 'bg-emerald-950/50 border-emerald-500/60 text-emerald-300 shadow-[0_0_12px_rgba(0,230,118,0.2)]'
              : 'bg-slate-900/80 border-slate-800 text-slate-400'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              data?.is_live_radar ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
            }`}
          />
          <span>{data?.is_live_radar ? 'LIVE RADAR' : 'SIMULATION'}</span>
        </div>

        {/* Basemap Switcher (Satellite vs Street) */}
        {setBasemapStyle && (
          <div className="flex items-center bg-slate-950/70 border border-slate-800/80 rounded-xl p-0.5">
            <button
              onClick={() => setBasemapStyle('satellite')}
              className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold transition-all ${
                basemapStyle === 'satellite'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(0,176,255,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sat
            </button>
            <button
              onClick={() => setBasemapStyle('streets')}
              className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold transition-all ${
                basemapStyle === 'streets'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(0,176,255,0.2)]'
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
          title={alertCount > 0 ? `${alertCount} Active Hazard Alerts` : 'No Active Hazards'}
          className={`relative p-1.5 rounded-xl border transition-all ${
            alertCount > 0
              ? 'bg-red-950/50 border-red-500/50 text-red-400 shadow-[0_0_14px_rgba(255,23,68,0.3)]'
              : 'bg-slate-900/70 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Bell size={15} />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[9px] font-bold text-white shadow-lg animate-pulse font-mono-num">
              {alertCount}
            </span>
          )}
        </button>

        {/* Connection status badge */}
        <div
          className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-xl bg-slate-950/70 border text-[10px] font-mono-num font-semibold"
          style={{ borderColor: `${connStatus.color}40`, color: connStatus.color }}
        >
          <ConnIcon size={12} />
          <span>{connStatus.label}</span>
        </div>

        {/* Timestamp */}
        {lastUpdated && (
          <div className="hidden xl:flex items-center gap-1 text-[10px] font-mono-num text-slate-400 bg-slate-950/50 px-2 py-1 rounded-lg border border-slate-800/60">
            <Clock size={11} className="text-slate-400" />
            <span>{lastUpdated}</span>
          </div>
        )}

        {/* Force refresh */}
        <button
          onClick={onRefresh}
          title="Force telemetry refresh"
          className="p-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800/80 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCcw size={14} />
        </button>
      </div>
    </header>
  );
}
