import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  MapContainer, TileLayer, ImageOverlay, Polygon, Tooltip, useMap
} from 'react-leaflet';
import {
  CloudRain, Zap, CloudSnow, Wind, RefreshCcw, Wifi,
  AlertTriangle, Info, Layers, ChevronDown, ChevronUp
} from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import './index.css';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const API_URL  = `${API_BASE}/api/v1/forecast/latest`;
const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws/forecast';

const BOUNDS = [[24.0, 89.8], [28.0, 96.0]];

// RainViewer weather maps manifest URL (free, no API key)
const RAINVIEWER_API = 'https://api.rainviewer.com/public/weather-maps.json';

// ── Auto-fit the map to the Assam bounding box ────────────────────────────────
function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (map && bounds) map.fitBounds(bounds, { padding: [10, 10], animate: false });
  }, [map, bounds]);
  return null;
}

// ── Dim everything outside our processing area ────────────────────────────────
const MASK_POSITIONS = [
  [[-90, -360], [90, -360], [90, 360], [-90, 360]],
  [[24.0, 89.8], [28.0, 89.8], [28.0, 96.0], [24.0, 96.0]]
];

// ── Layer configuration ───────────────────────────────────────────────────────
const RAIN_LAYERS = [
  { key: 'current', label: 'Now',    color: 'bg-blue-600' },
  { key: 'f30',     label: '+30m',   color: 'bg-green-600' },
  { key: 'f60',     label: '+60m',   color: 'bg-yellow-600' },
  { key: 'f90',     label: '+90m',   color: 'bg-orange-500' },
  { key: 'f180',    label: '+3 hr',  color: 'bg-red-500' },
  { key: 'f360',    label: '+6 hr',  color: 'bg-red-800' },
];

const HAZARD_LAYERS = [
  { key: 'cloudburst', label: 'Cloudburst', icon: CloudRain, color: 'bg-orange-600' },
  { key: 'hail',       label: 'Hail',       icon: CloudSnow, color: 'bg-blue-600' },
  { key: 'lightning',  label: 'Lightning',  icon: Zap,       color: 'bg-yellow-500' },
  { key: 'downburst',  label: 'Downburst',  icon: Wind,      color: 'bg-purple-600' },
];

// ── Legends ───────────────────────────────────────────────────────────────────
function LegendRain() {
  return (
    <div className="bg-gray-950/90 px-3 py-2 rounded-lg border border-gray-700 text-xs backdrop-blur-sm">
      <div className="flex justify-between text-gray-400 mb-1 font-medium">
        <span>Rain Rate (mm/hr)</span>
        <span className="text-gray-500 ml-4">IMD Scale</span>
      </div>
      <div className="h-2.5 w-full rounded" style={{
        background: 'linear-gradient(to right,#000080,#0000ff,#00ffff,#00ff00,#ffff00,#ff7f00,#ff0000,#7f0000)'
      }} />
      <div className="flex justify-between text-[10px] text-gray-400 mt-1 font-mono">
        <span>0</span><span>5</span><span>15</span><span>25</span><span>50+</span>
      </div>
    </div>
  );
}

function LegendHazard({ type }) {
  const configs = {
    cloudburst: { gradient: 'linear-gradient(to right,#ffffb2,#fed976,#feb24c,#fd8d3c,#f03b20,#bd0026)', label: 'Cloudburst Prob.' },
    hail:       { gradient: 'linear-gradient(to right,#f7fbff,#deebf7,#9ecae1,#3182bd,#08519c)', label: 'Hail Probability' },
    lightning:  { gradient: 'linear-gradient(to right,#ffffd4,#fed98e,#fe9929,#d95f0e,#993404)', label: 'Lightning Density' },
    downburst:  { gradient: 'linear-gradient(to right,#fcfbfd,#dadaeb,#9e9ac8,#756bb1,#54278f)', label: 'Downburst Risk' },
  };
  const cfg = configs[type] || configs.cloudburst;
  return (
    <div className="bg-gray-950/90 px-3 py-2 rounded-lg border border-gray-700 text-xs backdrop-blur-sm">
      <div className="text-gray-400 mb-1 font-medium">{cfg.label}</div>
      <div className="h-2.5 w-full rounded" style={{ background: cfg.gradient }} />
      <div className="flex justify-between text-[10px] text-gray-400 mt-1 font-mono">
        <span>0% (Low)</span><span>50%</span><span>100% (Critical)</span>
      </div>
    </div>
  );
}

// ── Severity styling ──────────────────────────────────────────────────────────
const SEVERITY = {
  RED:    { bg: 'bg-red-950/80',    border: 'border-red-600',    text: 'text-red-400',    badge: 'bg-red-600 text-white',    dot: 'bg-red-500' },
  ORANGE: { bg: 'bg-orange-950/80', border: 'border-orange-600', text: 'text-orange-400', badge: 'bg-orange-600 text-white', dot: 'bg-orange-500' },
  YELLOW: { bg: 'bg-yellow-950/80', border: 'border-yellow-600', text: 'text-yellow-400', badge: 'bg-yellow-600 text-white', dot: 'bg-yellow-400' },
  GREEN:  { bg: 'bg-green-950/80',  border: 'border-green-700',  text: 'text-green-400',  badge: 'bg-green-700 text-white',  dot: 'bg-green-500' },
};

const CONFIDENCE_CAVEATS = {
  current: 'Observation Frame — no model uncertainty',
  f30:     'High Skill — PySTEPS + U-Net blend',
  f60:     'High Skill — PySTEPS + U-Net blend',
  f90:     'Moderate Skill — PySTEPS + U-Net blend',
  f180:    'Advection Outlook (+3 hr) · Uncertainty increases past +2 hr',
  f360:    '⚠️ Extended Outlook (+6 hr) · Optical flow skill degrades significantly past +2 hr',
};

// ── Alert card component ──────────────────────────────────────────────────────
function AlertCard({ alert }) {
  const s = SEVERITY[alert.severity] || SEVERITY.GREEN;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`flex-shrink-0 w-72 ${s.bg} border ${s.border} rounded-xl p-3 shadow-lg`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.dot} ${alert.severity === 'RED' ? 'animate-pulse' : ''}`} />
          <span className={`text-sm font-bold ${s.text} leading-tight`}>{alert.title}</span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${s.badge}`}>{alert.severity}</span>
          <button onClick={() => setExpanded(e => !e)} className="text-gray-500 hover:text-gray-300 transition">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>
      {expanded && (
        <p className="text-xs text-gray-400 mt-2 leading-relaxed">{alert.reason}</p>
      )}
      {alert.eta_minutes && (
        <p className={`text-xs mt-1 ${s.text} font-mono`}>ETA: {alert.eta_minutes} min</p>
      )}
    </div>
  );
}

// ── Skeleton loading ──────────────────────────────────────────────────────────
function SkeletonScreen() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-6">
      <div className="h-16 bg-gray-800 rounded-xl animate-pulse mb-6" />
      <div className="h-10 bg-gray-800 rounded-xl animate-pulse mb-4" />
      <div className="h-[520px] bg-gray-900 rounded-xl animate-pulse mb-4 border border-gray-800" />
      <div className="grid grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="h-24 bg-gray-800 rounded-xl animate-pulse" />)}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [data,          setData]          = useState(null);
  const [error,         setError]         = useState(null);
  const [activeLayer,   setActiveLayer]   = useState('current');
  const [connectionMode,setConnectionMode]= useState('connecting');
  const [lastUpdated,   setLastUpdated]   = useState(null);
  const [rvTimestamp,   setRvTimestamp]   = useState(null);   // RainViewer radar timestamp
  const [showLayerPanel,setShowLayerPanel]= useState(true);
  const wsRef = useRef(null);

  // ── RainViewer: fetch latest radar timestamp once + refresh every 5 min ──
  const fetchRainViewer = useCallback(async () => {
    try {
      const res  = await fetch(RAINVIEWER_API);
      const json = await res.json();
      const past = json?.radar?.past;
      if (past && past.length > 0) {
        setRvTimestamp(past[past.length - 1].time);
      }
    } catch {
      // RainViewer unavailable — silent fail, model overlays still work
    }
  }, []);

  useEffect(() => {
    fetchRainViewer();
    const t = setInterval(fetchRainViewer, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [fetchRainViewer]);

  // ── Backend data fetch + WebSocket ───────────────────────────────────────
  const fetchHttpData = useCallback(async () => {
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
      setLastUpdated(new Date().toLocaleTimeString());
      setConnectionMode(prev => prev === 'ws' ? 'ws' : 'http');
    } catch (err) {
      setError(err.message);
      setConnectionMode('error');
    }
  }, []);

  useEffect(() => {
    const connectWS = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen  = () => { setConnectionMode('ws'); setError(null); };
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'forecast' && msg.data) {
              setData(msg.data);
              setLastUpdated(new Date().toLocaleTimeString());
            } else if (msg.type === 'frame_ingested') {
              fetchHttpData();
            }
          } catch {}
        };
        ws.onerror = () => setConnectionMode('http');
        ws.onclose = () => setConnectionMode(p => p === 'ws' ? 'http' : p);
      } catch {
        setConnectionMode('http');
      }
    };

    connectWS();
    // Initial HTTP fetch — WS delivers on open, but HTTP covers the gap if WS is slow
    const initialTimer = setTimeout(fetchHttpData, 800);
    const pollTimer    = setInterval(fetchHttpData, 10000);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(pollTimer);
      wsRef.current?.close();
    };
  }, [fetchHttpData]);

  // ── Memoize the active overlay image so layer switches don't re-render map
  const overlayUrl = useMemo(() => data?.images?.[activeLayer], [data, activeLayer]);

  // ── RainViewer tile URL ───────────────────────────────────────────────────
  const rvTileUrl = useMemo(() => {
    if (!rvTimestamp) return null;
    return `https://tilecache.rainviewer.com/v2/radar/${rvTimestamp}/256/{z}/{x}/{y}/4/1_1.png`;
  }, [rvTimestamp]);

  // ── Determine active polygon set ─────────────────────────────────────────
  const activePolygons = useMemo(() => {
    if (!data) return [];
    if (activeLayer === 'cloudburst') return (data.cloudburst_polygons || []).map(p => ({ ...p, color: '#ef4444' }));
    if (activeLayer === 'lightning')  return (data.lightning_polygons  || []).map(p => ({ ...p, color: '#f59e0b' }));
    return [];
  }, [data, activeLayer]);

  // ── Loading / error screen ───────────────────────────────────────────────
  if (!data) {
    return (
      <div className="min-h-screen bg-gray-950">
        <SkeletonScreen />
        {error && (
          <div className="fixed inset-0 flex items-center justify-center p-4 bg-gray-950/80 z-50">
            <div className="bg-red-950/90 border border-red-700 rounded-xl p-6 max-w-sm text-center text-white shadow-2xl">
              <AlertTriangle className="mx-auto text-red-400 mb-3" size={32} />
              <p className="font-bold mb-1">Backend connection failed</p>
              <p className="text-sm text-gray-400 mb-4">{error}</p>
              <button onClick={fetchHttpData}
                className="px-4 py-2 bg-red-700 hover:bg-red-600 rounded-lg text-sm font-medium transition">
                Retry
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  const isRainLayer   = RAIN_LAYERS.some(l => l.key === activeLayer);
  const activeHazard  = isRainLayer ? null : activeLayer;

  // ── Derive top-level severity for header badge ────────────────────────────
  const alerts         = data.alerts || [];
  const worstSeverity  = ['RED','ORANGE','YELLOW','GREEN'].find(s => alerts.some(a => a.severity === s)) || 'GREEN';
  const worstStyle     = SEVERITY[worstSeverity];
  const atm            = data.atmospheric_context || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans flex flex-col">

      {/* ── Header ── */}
      <header className="px-4 md:px-6 py-3 border-b border-gray-800 flex items-center justify-between gap-4 flex-wrap bg-gray-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <CloudRain className="text-blue-500" size={28} />
          <div>
            <h1 className="text-lg md:text-xl font-bold text-white leading-tight">NowCast Fusion</h1>
            <p className="text-[11px] text-gray-400">Convective EWS · North-East India (Assam)</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Worst-severity pill */}
          <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${worstStyle.bg} ${worstStyle.border} ${worstStyle.text}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${worstStyle.dot} ${worstSeverity === 'RED' ? 'animate-pulse' : ''}`} />
            {worstSeverity === 'GREEN' ? 'ALL CLEAR' : `${worstSeverity} ALERT`}
          </span>

          {/* Connection mode */}
          {connectionMode === 'ws' ? (
            <span className="flex items-center gap-1 px-2.5 py-1 bg-green-950/70 border border-green-700 text-green-400 text-xs rounded-full">
              <Wifi size={11} className="animate-pulse" /><span>Live</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 px-2.5 py-1 bg-yellow-950/70 border border-yellow-700 text-yellow-400 text-xs rounded-full">
              <RefreshCcw size={11} /><span>Polling 10s</span>
            </span>
          )}

          {rvTimestamp && (
            <span className="text-[10px] text-gray-500 font-mono hidden md:block">
              Radar: {new Date(rvTimestamp * 1000).toLocaleTimeString()}
            </span>
          )}
          {lastUpdated && (
            <span className="text-[10px] text-gray-500 font-mono hidden md:block">Model: {lastUpdated}</span>
          )}

          <button onClick={fetchHttpData} title="Force refresh"
            className="p-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-md transition">
            <RefreshCcw size={13} />
          </button>
        </div>
      </header>

      {/* ── Alert Banner ── */}
      <div className="px-4 md:px-6 py-2 bg-gray-900/60 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-1.5">
          <AlertTriangle size={13} className="text-gray-400 flex-shrink-0" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
            Active Alerts — Model-Derived (IMD Scale)
          </span>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
          {alerts.map((alert, i) => <AlertCard key={i} alert={alert} />)}
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="flex flex-col flex-1 px-4 md:px-6 py-4 gap-4">

        {/* Map + Layer Switcher row */}
        <div className="flex gap-4 flex-col lg:flex-row">

          {/* ── Single unified map ── */}
          <div className="flex-1 bg-gray-900 rounded-xl overflow-hidden border border-gray-800 shadow-xl flex flex-col min-h-[480px]">

            {/* Map sub-header */}
            <div className="px-4 py-2 bg-gray-800/80 border-b border-gray-700 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Layers size={16} className="text-blue-400" />
                <span className="text-sm font-semibold">
                  {isRainLayer
                    ? `Precipitation — ${RAIN_LAYERS.find(l=>l.key===activeLayer)?.label}`
                    : `${HAZARD_LAYERS.find(l=>l.key===activeLayer)?.label} Risk Map`}
                </span>
                {rvTimestamp && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-blue-900/60 border border-blue-700 text-blue-400 rounded font-mono">
                    Live Radar
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <Info size={12} className="text-blue-400" />
                <span>{isRainLayer ? CONFIDENCE_CAVEATS[activeLayer] : 'IMD Threshold Verified · Lead time: +30 min'}</span>
              </div>
            </div>

            {/* Leaflet map */}
            <div className="flex-1 relative">
              <MapContainer
                bounds={BOUNDS}
                boundsOptions={{ padding: [10, 10] }}
                maxBounds={BOUNDS}
                maxBoundsViscosity={1.0}
                scrollWheelZoom={true}
                className="h-full w-full"
                style={{ minHeight: '420px', background: '#0f172a' }}
              >
                <FitBounds bounds={BOUNDS} />

                {/* Base map */}
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
                  subdomains="abcd"
                  maxZoom={19}
                />

                {/* RainViewer live radar layer */}
                {rvTileUrl && (
                  <TileLayer
                    url={rvTileUrl}
                    attribution='Weather radar &copy; <a href="https://www.rainviewer.com/">RainViewer</a>'
                    opacity={0.5}
                    zIndex={200}
                  />
                )}

                {/* Dim mask outside Assam */}
                <Polygon
                  positions={MASK_POSITIONS}
                  pathOptions={{ color: 'none', fillColor: '#000', fillOpacity: 0.65 }}
                />

                {/* Model overlay */}
                {overlayUrl && (
                  <ImageOverlay url={overlayUrl} bounds={BOUNDS} opacity={0.82} zIndex={300} />
                )}

                {/* Hazard polygons */}
                {activePolygons.map((poly, i) => (
                  <Polygon key={i} positions={poly.bounds}
                    pathOptions={{ color: poly.color, weight: 1.5, fillColor: poly.color, fillOpacity: 0.3 }}>
                    <Tooltip>
                      <span className="font-bold">High Risk Zone</span><br />
                      Risk: {(poly.risk * 100).toFixed(0)}%
                    </Tooltip>
                  </Polygon>
                ))}
              </MapContainer>

              {/* Legend — floating bottom-left */}
              <div className="absolute bottom-3 left-3 z-[1000] w-56">
                {isRainLayer ? <LegendRain /> : <LegendHazard type={activeLayer} />}
              </div>
            </div>
          </div>

          {/* ── Layer Switcher Panel ── */}
          <div className="lg:w-48 flex flex-col gap-2">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 shadow-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Layer</span>
                <button onClick={() => setShowLayerPanel(p => !p)}
                  className="text-gray-500 hover:text-gray-300 transition lg:hidden">
                  {showLayerPanel ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                </button>
              </div>

              {(showLayerPanel) && (
                <>
                  {/* Rain layers */}
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5 font-semibold">Precipitation</p>
                  <div className="flex flex-col gap-1 mb-3">
                    {RAIN_LAYERS.map(({ key, label, color }) => (
                      <button key={key} onClick={() => setActiveLayer(key)}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                          activeLayer === key
                            ? `${color} text-white shadow-md`
                            : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                        }`}>
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* Hazard layers */}
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5 font-semibold">Hazard Products</p>
                  <div className="flex flex-col gap-1">
                    {HAZARD_LAYERS.map(({ key, label, icon: Icon, color }) => (
                      <button key={key} onClick={() => setActiveLayer(key)}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
                          activeLayer === key
                            ? `${color} text-white shadow-md`
                            : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                        }`}>
                        <Icon size={12} />
                        {label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Buffer indicator */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Buffer</p>
              <p className="text-xl font-bold text-white">{data.buffer_size}</p>
              <p className="text-[10px] text-gray-500">frames</p>
            </div>
          </div>
        </div>

        {/* ── Atmospheric Context Row ── */}
        {atm.source && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* CAPE */}
            <div className="bg-gray-900 border border-yellow-600/30 rounded-xl p-3 shadow-md">
              <p className="text-yellow-400 text-[10px] font-semibold uppercase tracking-wider mb-1">⚡ CAPE</p>
              <p className="text-2xl font-bold text-white">{atm.cape?.toFixed(0) ?? '--'}</p>
              <p className="text-gray-400 text-[11px]">J/kg</p>
              <p className={`text-[11px] font-medium mt-1 ${
                atm.cape > 2000 ? 'text-red-400' : atm.cape > 1000 ? 'text-yellow-400' : 'text-green-400'
              }`}>
                {atm.cape > 2000 ? '🔴 Extreme' : atm.cape > 1000 ? '🟡 Active' : '🟢 Stable'}
              </p>
            </div>

            {/* Wind */}
            <div className="bg-gray-900 border border-blue-600/30 rounded-xl p-3 shadow-md">
              <p className="text-blue-400 text-[10px] font-semibold uppercase tracking-wider mb-1">💨 Wind</p>
              <p className="text-2xl font-bold text-white">{atm.wind_speed?.toFixed(1) ?? '--'}</p>
              <p className="text-gray-400 text-[11px]">m/s @ 10m AGL</p>
              <p className="text-gray-500 text-[11px] mt-1">{atm.wind_direction?.toFixed(0) ?? '--'}° direction</p>
            </div>

            {/* Humidity */}
            <div className="bg-gray-900 border border-cyan-600/30 rounded-xl p-3 shadow-md">
              <p className="text-cyan-400 text-[10px] font-semibold uppercase tracking-wider mb-1">💧 Humidity</p>
              <p className="text-2xl font-bold text-white">{atm.humidity?.toFixed(0) ?? '--'}%</p>
              <p className="text-gray-400 text-[11px]">2m Relative Humidity</p>
              <p className="text-gray-500 text-[11px] mt-1">
                {atm.humidity >= 85 ? '🔵 High moisture' : '⚪ Normal'}
              </p>
            </div>

            {/* Model status */}
            <div className="bg-gray-900 border border-purple-600/30 rounded-xl p-3 shadow-md">
              <p className="text-purple-400 text-[10px] font-semibold uppercase tracking-wider mb-1">🛰️ Model</p>
              <p className="text-sm font-bold text-white leading-tight">U-Net + PySTEPS</p>
              <p className="text-gray-400 text-[11px]">SRTM 1km downscale</p>
              <p className="text-gray-500 text-[11px] mt-1">
                {atm.source === 'open-meteo' ? '🟢 Live atm. data' : '🟡 Fallback data'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
