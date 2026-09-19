import React, { useState, useMemo } from 'react';
import { CloudRain, Activity, RefreshCcw } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import 'leaflet/dist/leaflet.css';
import './index.css';

import { useForecast } from './hooks/useForecast';
import { useUserLocation } from './hooks/useUserLocation';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MapPanel from './components/MapPanel';
import AlertsPanel from './components/AlertsPanel';
import TelemetryRibbon from './components/TelemetryRibbon';

export default function App() {
  // ── State Management for Segmented Controls & Drawers ─────────────────────
  const [radarType, setRadarType] = useState('precipitation'); // 'precipitation' | 'cloudburst' | 'hail' | 'lightning' | 'downburst'
  const [timeOffset, setTimeOffset] = useState('current'); // 'current' | 'f30' | 'f60' | 'f90' | 'f180' | 'f360'
  const [activeLayer, setActiveLayer] = useState('current');
  const [basemapStyle, setBasemapStyle] = useState('satellite'); // 'satellite' | 'streets'
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);

  const {
    data,
    error,
    connectionMode,
    lastUpdated,
    rvManifest,
    syncingRadar,
    displaySeverity,
    fetchHttpData,
    syncLiveRadar,
  } = useForecast();

  const {
    userLoc,
    localWeather,
    locAddress,
    locating,
    flyTarget,
    showLocCard,
    setShowLocCard,
    locateUser,
  } = useUserLocation();

  // ── RainViewer v3 tile URL computation ──────────────────────────────────────
  const rvFrames = rvManifest?.radar?.past ?? [];
  const rvLatestTime = rvFrames.length > 0 ? rvFrames[rvFrames.length - 1].time : null;
  const rvDisplayTime = rvLatestTime ? new Date(rvLatestTime * 1000).toLocaleTimeString() : null;
  const rvHost = rvManifest?.host ?? 'https://tilecache.rainviewer.com';
  const rvPath = rvFrames.length > 0 ? rvFrames[rvFrames.length - 1].path : null;

  const rvTileUrl = useMemo(() => {
    if (!rvPath) return null;
    return `${rvHost}${rvPath}/256/{z}/{x}/{y}/4/1_1.png`;
  }, [rvHost, rvPath]);

  // ── Loading / Error View (HUD Style) ───────────────────────────────────────
  if (!data) {
    return (
      <div className="relative w-screen h-screen flex items-center justify-center bg-[#0B101D] text-slate-100 overflow-hidden select-none">
        {/* Subtle HUD background grid lines */}
        <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-25" />

        <div className="relative z-10 w-full max-w-md p-8 rounded-2xl backdrop-blur-xl bg-[#161F33]/90 border border-slate-800/80 shadow-2xl shadow-black text-center">
          {/* Brand Icon with glowing ring */}
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center shadow-[0_0_20px_rgba(0,176,255,0.3)]">
              <CloudRain size={28} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(0,176,255,0.8)]" />
            </div>
            <div className="text-left">
              <h1 className="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
                NowCast Fusion
                <span className="text-[10px] font-mono-num font-bold px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                  HUD
                </span>
              </h1>
              <p className="text-xs text-slate-400">Convective EWS · North-East India</p>
            </div>
          </div>

          {error ? (
            <>
              <div className="my-6 relative w-16 h-16 mx-auto">
                <div className="absolute inset-0 rounded-full border-2 border-red-900/50 border-t-red-500 animate-spin" />
                <Activity size={24} className="absolute inset-0 m-auto text-red-400" />
              </div>

              <h2 className="text-base font-bold text-slate-200 mb-1 font-mono-num">
                Connecting to Convective Core…
              </h2>
              <p className="text-xs text-slate-400 mb-4">
                Auto-retrying WebSocket / HTTP sync with FastAPI backend
              </p>

              <div className="p-3 mb-5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-left font-mono-num text-xs">
                <span className="text-[10px] text-slate-500 block uppercase tracking-wider mb-1">
                  Local Command
                </span>
                <code className="text-cyan-300 text-[11px] select-all">
                  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
                </code>
              </div>

              <button
                onClick={fetchHttpData}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs transition-all shadow-[0_0_15px_rgba(255,23,68,0.4)]"
              >
                <RefreshCcw size={14} /> Retry Handshake
              </button>
            </>
          ) : (
            <>
              <div className="my-8 relative w-16 h-16 mx-auto">
                <div className="absolute inset-0 rounded-full border-2 border-cyan-900/50 border-t-cyan-400 animate-spin" />
                <Activity size={24} className="absolute inset-0 m-auto text-cyan-400 animate-pulse" />
              </div>
              <h2 className="text-sm font-bold text-slate-300 font-mono-num tracking-wide">
                INITIALIZING RADAR TELEMETRY…
              </h2>
              <p className="text-xs text-slate-400 mt-1">Loading IMD DWR sweeps & AI nowcast tensors</p>
            </>
          )}
        </div>
      </div>
    );
  }

  // ── Main Dashboard View: Fullscreen Map Viewport with Floating Panels ─────────
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#090D16] text-slate-100 select-none font-sans">
      {/* ── 1. Main Viewport: Centered Full-Screen Leaflet Satellite Map Canvas ── */}
      <MapPanel
        data={data}
        activeLayer={activeLayer}
        basemapStyle={basemapStyle}
        rvTileUrl={rvTileUrl}
        userLoc={userLoc}
        localWeather={localWeather}
        locAddress={locAddress}
        flyTarget={flyTarget}
        showLocCard={showLocCard}
        setShowLocCard={setShowLocCard}
      />

      {/* ── 2. Top Floating Navigation (Glassmorphic Bar) ── */}
      <div className="fixed top-4 inset-x-6 z-[1000]">
        <Header
          displaySeverity={displaySeverity}
          syncingRadar={syncingRadar}
          syncLiveRadar={syncLiveRadar}
          locating={locating}
          locateUser={locateUser}
          connectionMode={connectionMode}
          data={data}
          lastUpdated={lastUpdated}
          onRefresh={fetchHttpData}
          alertCount={(data.alerts ?? []).length}
          basemapStyle={basemapStyle}
          setBasemapStyle={setBasemapStyle}
          leftOpen={leftOpen}
          setLeftOpen={setLeftOpen}
          rightOpen={rightOpen}
          setRightOpen={setRightOpen}
        />
      </div>

      {/* ── 3. Left Sidebar: Radar & Convective Control Panel ── */}
      <AnimatePresence>
        {leftOpen ? (
          <Sidebar
            key="sidebar-left"
            radarType={radarType}
            setRadarType={setRadarType}
            timeOffset={timeOffset}
            setTimeOffset={setTimeOffset}
            setActiveLayer={setActiveLayer}
            data={data}
            rvDisplayTime={rvDisplayTime}
            onClose={() => setLeftOpen(false)}
          />
        ) : (
          <button
            key="btn-left-tab"
            onClick={() => setLeftOpen(true)}
            title="Expand Radar Controls"
            className="fixed top-20 left-6 z-[900] flex items-center gap-1.5 px-3 py-1.5 rounded-xl backdrop-blur-xl bg-slate-900/60 border border-white/10 text-slate-300 hover:text-white hover:border-white/20 shadow-2xl shadow-black/80 transition-all text-xs font-medium"
          >
            <Activity size={13} className="text-sky-400" />
            <span>Radar Controls</span>
          </button>
        )}
      </AnimatePresence>

      {/* ── 4. Right Floating Sidebar: Active Hazards & Radar Telemetry ── */}
      <AnimatePresence>
        {rightOpen ? (
          <AlertsPanel
            key="panel-right"
            alerts={data.alerts ?? []}
            atm={data.atmospheric_context ?? {}}
            rvDisplayTime={rvDisplayTime}
            onClose={() => setRightOpen(false)}
          />
        ) : (
          <button
            key="btn-right-tab"
            onClick={() => setRightOpen(true)}
            title="Expand Hazard Telemetry"
            className="fixed top-20 right-6 z-[900] flex items-center gap-1.5 px-3 py-1.5 rounded-xl backdrop-blur-xl bg-slate-900/60 border border-white/10 text-slate-300 hover:text-white hover:border-white/20 shadow-2xl shadow-black/80 transition-all text-xs font-medium"
          >
            <span>Hazards ({(data.alerts ?? []).length})</span>
          </button>
        )}
      </AnimatePresence>

      {/* ── 5. Bottom Floating Telemetry Ribbon ── */}
      <TelemetryRibbon
        atm={data.atmospheric_context ?? {}}
        maxRain={data.max_val ?? null}
        displaySeverity={displaySeverity}
      />
    </div>
  );
}

