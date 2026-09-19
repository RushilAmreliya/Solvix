import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  MapContainer, TileLayer, ImageOverlay, Polygon, Tooltip, useMap
} from 'react-leaflet';
import {
  CloudRain, Zap, CloudSnow, Wind, RefreshCcw, Wifi, WifiOff,
  AlertTriangle, Layers, ChevronRight, Activity, Thermometer,
  Droplets, Navigation, Cpu, Shield, Clock, Radio
} from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import './index.css';

// ── API Config ────────────────────────────────────────────────────────────────
const defaultApiHost = typeof window !== 'undefined' && window.location.hostname
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'http://localhost:8000';
const API_BASE = (import.meta.env.VITE_API_URL || defaultApiHost).replace(/\/$/, '');
const API_URL  = `${API_BASE}/api/v1/forecast/latest`;
const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws/forecast';

const BOUNDS = [[24.0, 89.8], [28.0, 96.0]];
const RAINVIEWER_API = 'https://api.rainviewer.com/public/weather-maps.json';

// ── Map helpers ───────────────────────────────────────────────────────────────
function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (map && bounds) map.fitBounds(bounds, { padding: [8, 8], animate: false });
  }, [map, bounds]);
  return null;
}

const MASK_POSITIONS = [
  [[-90, -360], [90, -360], [90, 360], [-90, 360]],
  [[24.0, 89.8], [28.0, 89.8], [28.0, 96.0], [24.0, 96.0]]
];

// ── Layer configuration ───────────────────────────────────────────────────────
const RAIN_LAYERS = [
  { key: 'current', label: 'Now',    sublabel: 'Observed',  color: '#3b82f6', ring: 'ring-blue-500' },
  { key: 'f30',     label: '+30m',   sublabel: 'High skill',color: '#22c55e', ring: 'ring-green-500' },
  { key: 'f60',     label: '+60m',   sublabel: 'High skill',color: '#eab308', ring: 'ring-yellow-500' },
  { key: 'f90',     label: '+90m',   sublabel: 'Moderate',  color: '#f97316', ring: 'ring-orange-500' },
  { key: 'f180',    label: '+3 hr',  sublabel: 'Outlook',   color: '#ef4444', ring: 'ring-red-500' },
  { key: 'f360',    label: '+6 hr',  sublabel: 'Extended',  color: '#991b1b', ring: 'ring-red-900' },
];

const HAZARD_LAYERS = [
  { key: 'cloudburst', label: 'Cloudburst', icon: CloudRain, color: '#ea580c', ring: 'ring-orange-500' },
  { key: 'hail',       label: 'Hail',       icon: CloudSnow, color: '#2563eb', ring: 'ring-blue-500'   },
  { key: 'lightning',  label: 'Lightning',  icon: Zap,       color: '#ca8a04', ring: 'ring-yellow-500' },
  { key: 'downburst',  label: 'Downburst',  icon: Wind,      color: '#7c3aed', ring: 'ring-purple-500' },
];

// ── Severity config ───────────────────────────────────────────────────────────
const SEVERITY = {
  RED:    { bg: '#450a0a', border: '#dc2626', text: '#f87171', badge: '#dc2626', glow: 'shadow-red-900' },
  ORANGE: { bg: '#431407', border: '#ea580c', text: '#fb923c', badge: '#ea580c', glow: 'shadow-orange-900' },
  YELLOW: { bg: '#422006', border: '#ca8a04', text: '#facc15', badge: '#ca8a04', glow: 'shadow-yellow-900' },
  GREEN:  { bg: '#052e16', border: '#16a34a', text: '#4ade80', badge: '#15803d', glow: 'shadow-green-900' },
};

const CONFIDENCE_CAVEATS = {
  current: 'Observation frame — no model uncertainty',
  f30:     'PySTEPS + U-Net blend · High skill',
  f60:     'PySTEPS + U-Net blend · High skill',
  f90:     'PySTEPS + U-Net blend · Moderate skill',
  f180:    'Advection outlook · Skill degrades past +2 hr',
  f360:    'Extended outlook · Low confidence beyond +2 hr',
};

// ── Rain Legend ───────────────────────────────────────────────────────────────
function LegendRain() {
  const stops = [
    { mm: '0',   color: '#000080' },
    { mm: '5',   color: '#0000ff' },
    { mm: '15',  color: '#00ffff' },
    { mm: '25',  color: '#00ff00' },
    { mm: '50+', color: '#ff0000' },
  ];
  return (
    <div className="legend-card">
      <div className="legend-title">Rain Rate · mm/hr · IMD Scale</div>
      <div className="legend-bar" style={{
        background: 'linear-gradient(to right,#000080,#0000ff,#00ffff,#00ff00,#ffff00,#ff7f00,#ff0000)'
      }} />
      <div className="legend-labels">
        {stops.map(s => (
          <span key={s.mm} style={{ color: s.color, fontWeight: 700 }}>{s.mm}</span>
        ))}
      </div>
    </div>
  );
}

function LegendHazard({ type }) {
  const configs = {
    cloudburst: { g: 'linear-gradient(to right,#ffffb2,#feb24c,#f03b20,#bd0026)', label: 'Cloudburst Probability' },
    hail:       { g: 'linear-gradient(to right,#f7fbff,#9ecae1,#3182bd,#08519c)', label: 'Hail Probability' },
    lightning:  { g: 'linear-gradient(to right,#ffffd4,#fe9929,#d95f0e,#993404)', label: 'Lightning Density' },
    downburst:  { g: 'linear-gradient(to right,#fcfbfd,#9e9ac8,#756bb1,#54278f)', label: 'Downburst Risk' },
  };
  const cfg = configs[type] || configs.cloudburst;
  return (
    <div className="legend-card">
      <div className="legend-title">{cfg.label}</div>
      <div className="legend-bar" style={{ background: cfg.g }} />
      <div className="legend-labels">
        <span>Low</span><span>Moderate</span><span>Critical</span>
      </div>
    </div>
  );
}

// ── Alert Item ────────────────────────────────────────────────────────────────
function AlertItem({ alert }) {
  const s = SEVERITY[alert.severity] || SEVERITY.GREEN;
  const icons = { RED: '🔴', ORANGE: '🟠', YELLOW: '🟡', GREEN: '🟢' };
  return (
    <div className="alert-item" style={{ background: s.bg, borderColor: s.border }}>
      <div className="alert-header">
        <span className="alert-icon">{icons[alert.severity] || '🟢'}</span>
        <div className="alert-body">
          <div className="alert-title" style={{ color: s.text }}>{alert.title}</div>
          {alert.reason && <div className="alert-reason">{alert.reason}</div>}
        </div>
        <div className="alert-meta">
          <span className="alert-badge" style={{ background: s.badge }}>{alert.severity}</span>
          {alert.eta_minutes && (
            <span className="alert-eta">ETA {alert.eta_minutes}m</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <div className="skeleton-root">
      <div className="skeleton-header" />
      <div className="skeleton-body">
        <div className="skeleton-sidebar" />
        <div className="skeleton-main" />
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, unit, sub, accentColor }) {
  return (
    <div className="stat-card" style={{ borderColor: accentColor + '44' }}>
      <div className="stat-icon" style={{ color: accentColor }}><Icon size={18} /></div>
      <div className="stat-content">
        <div className="stat-label" style={{ color: accentColor }}>{label}</div>
        <div className="stat-value">{value}<span className="stat-unit">{unit}</span></div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [data,           setData]           = useState(null);
  const [error,          setError]          = useState(null);
  const [activeLayer,    setActiveLayer]    = useState('current');
  const [connectionMode, setConnectionMode] = useState('connecting');
  const [lastUpdated,    setLastUpdated]    = useState(null);
  const [rvTimestamp,    setRvTimestamp]    = useState(null);
  const wsRef = useRef(null);

  // ── RainViewer ────────────────────────────────────────────────────────────
  const fetchRainViewer = useCallback(async () => {
    try {
      const res  = await fetch(RAINVIEWER_API);
      const json = await res.json();
      const past = json?.radar?.past;
      if (past && past.length > 0) setRvTimestamp(past[past.length - 1].time);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchRainViewer();
    const t = setInterval(fetchRainViewer, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [fetchRainViewer]);

  // ── Data fetch / WebSocket ────────────────────────────────────────────────
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
        ws.onopen    = () => { setConnectionMode('ws'); setError(null); };
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
      } catch { setConnectionMode('http'); }
    };
    connectWS();
    const initialTimer = setTimeout(fetchHttpData, 800);
    const pollTimer    = setInterval(fetchHttpData, 10000);
    return () => {
      clearTimeout(initialTimer);
      clearInterval(pollTimer);
      wsRef.current?.close();
    };
  }, [fetchHttpData]);

  // ── Derived data ──────────────────────────────────────────────────────────
  const overlayUrl = useMemo(() => data?.images?.[activeLayer], [data, activeLayer]);
  const rvTileUrl  = useMemo(() => {
    if (!rvTimestamp) return null;
    return `https://tilecache.rainviewer.com/v2/radar/${rvTimestamp}/256/{z}/{x}/{y}/4/1_1.png`;
  }, [rvTimestamp]);
  const activePolygons = useMemo(() => {
    if (!data) return [];
    if (activeLayer === 'cloudburst') return (data.cloudburst_polygons || []).map(p => ({ ...p, color: '#ef4444' }));
    if (activeLayer === 'lightning')  return (data.lightning_polygons  || []).map(p => ({ ...p, color: '#f59e0b' }));
    return [];
  }, [data, activeLayer]);

  const isRainLayer  = RAIN_LAYERS.some(l => l.key === activeLayer);
  const activeRainCfg   = RAIN_LAYERS.find(l => l.key === activeLayer);
  const activeHazardCfg = HAZARD_LAYERS.find(l => l.key === activeLayer);

  // ── Loading / Error ───────────────────────────────────────────────────────
  if (!data) {
    return (
      <div className="app-root">
        <Skeleton />
        {error && (
          <div className="error-overlay">
            <div className="error-card">
              <AlertTriangle size={36} color="#f87171" />
              <div className="error-title">Backend Unreachable</div>
              <div className="error-msg">{error}</div>
              <button className="error-btn" onClick={fetchHttpData}>
                <RefreshCcw size={14} /> Retry
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  const alerts        = data.alerts || [];
  const worstSeverity = ['RED','ORANGE','YELLOW','GREEN'].find(s => alerts.some(a => a.severity === s)) || 'GREEN';
  const worstStyle    = SEVERITY[worstSeverity];
  const atm           = data.atmospheric_context || {};

  const statusLabel = {
    ws:   { icon: Wifi,    label: 'Live WebSocket', color: '#4ade80' },
    http: { icon: Radio,   label: 'Polling 10s',    color: '#facc15' },
    error:{ icon: WifiOff, label: 'Disconnected',   color: '#f87171' },
    connecting: { icon: Activity, label: 'Connecting…', color: '#94a3b8' },
  }[connectionMode] || { icon: Activity, label: connectionMode, color: '#94a3b8' };
  const StatusIcon = statusLabel.icon;

  return (
    <div className="app-root">
      {/* ══ HEADER ══════════════════════════════════════════════════════════ */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon-wrap">
            <CloudRain size={22} color="#60a5fa" />
          </div>
          <div>
            <div className="brand-name">NowCast Fusion</div>
            <div className="brand-sub">Convective EWS · North-East India (Assam)</div>
          </div>
        </div>

        <div className="header-center">
          <div className="severity-pill" style={{ background: worstStyle.bg, borderColor: worstStyle.border }}>
            <span className={`sev-dot ${worstSeverity === 'RED' ? 'pulse' : ''}`}
              style={{ background: worstStyle.text }} />
            <span style={{ color: worstStyle.text, fontWeight: 700, fontSize: 13 }}>
              {worstSeverity === 'GREEN' ? 'ALL CLEAR' : `${worstSeverity} ALERT`}
            </span>
          </div>
        </div>

        <div className="header-right">
          <div className="conn-status" style={{ borderColor: statusLabel.color + '55' }}>
            <StatusIcon size={13} style={{ color: statusLabel.color }} />
            <span style={{ color: statusLabel.color, fontSize: 12 }}>{statusLabel.label}</span>
          </div>
          {lastUpdated && (
            <div className="update-time">
              <Clock size={11} color="#64748b" />
              <span>{lastUpdated}</span>
            </div>
          )}
          <button className="refresh-btn" onClick={fetchHttpData} title="Force refresh">
            <RefreshCcw size={14} />
          </button>
        </div>
      </header>

      {/* ══ BODY ════════════════════════════════════════════════════════════ */}
      <div className="app-body">

        {/* ── LEFT SIDEBAR ── */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-section-label">
              <Layers size={12} />Precipitation
            </div>
            {RAIN_LAYERS.map(l => (
              <button
                key={l.key}
                className={`layer-btn ${activeLayer === l.key ? 'layer-btn-active' : ''}`}
                style={activeLayer === l.key ? { borderColor: l.color, background: l.color + '22', color: '#fff' } : {}}
                onClick={() => setActiveLayer(l.key)}
              >
                <span className="layer-dot" style={{ background: l.color }} />
                <span className="layer-btn-main">{l.label}</span>
                <span className="layer-btn-sub">{l.sublabel}</span>
                {activeLayer === l.key && <ChevronRight size={12} style={{ color: l.color, marginLeft: 'auto' }} />}
              </button>
            ))}
          </div>

          <div className="sidebar-section">
            <div className="sidebar-section-label">
              <Shield size={12} />Hazard Products
            </div>
            {HAZARD_LAYERS.map(({ key, label, icon: Icon, color }) => (
              <button
                key={key}
                className={`layer-btn ${activeLayer === key ? 'layer-btn-active' : ''}`}
                style={activeLayer === key ? { borderColor: color, background: color + '22', color: '#fff' } : {}}
                onClick={() => setActiveLayer(key)}
              >
                <Icon size={13} style={{ color: activeLayer === key ? color : '#64748b', flexShrink: 0 }} />
                <span className="layer-btn-main">{label}</span>
                {activeLayer === key && <ChevronRight size={12} style={{ color, marginLeft: 'auto' }} />}
              </button>
            ))}
          </div>

          {/* Buffer indicator */}
          <div className="buffer-card">
            <div className="buffer-label">Frame Buffer</div>
            <div className="buffer-value">{data.buffer_size}</div>
            <div className="buffer-sub">frames cached</div>
            <div className="buffer-bar">
              <div className="buffer-fill" style={{ width: `${Math.min(100, (data.buffer_size / 20) * 100)}%` }} />
            </div>
          </div>
        </aside>

        {/* ── MAIN PANEL ── */}
        <main className="main-panel">
          {/* Map header */}
          <div className="map-header">
            <div className="map-header-left">
              {isRainLayer ? (
                <>
                  <span className="map-layer-dot" style={{ background: activeRainCfg?.color }} />
                  <span className="map-title">Precipitation · {activeRainCfg?.label}</span>
                </>
              ) : (
                <>
                  <span className="map-layer-dot" style={{ background: activeHazardCfg?.color }} />
                  <span className="map-title">{activeHazardCfg?.label} Risk</span>
                </>
              )}
              {rvTimestamp && (
                <span className="live-badge">
                  <Radio size={10} className="live-dot" />LIVE Radar
                </span>
              )}
            </div>
            <div className="map-caveat">
              {isRainLayer ? CONFIDENCE_CAVEATS[activeLayer] : 'IMD threshold verified · Lead time +30 min'}
            </div>
          </div>

          {/* Leaflet map */}
          <div className="map-wrap">
            <MapContainer
              bounds={BOUNDS}
              boundsOptions={{ padding: [8, 8] }}
              maxBounds={BOUNDS}
              maxBoundsViscosity={1.0}
              scrollWheelZoom={true}
              className="map-container"
              style={{ background: '#0f172a' }}
            >
              <FitBounds bounds={BOUNDS} />
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
                subdomains="abcd"
                maxZoom={19}
              />
              {rvTileUrl && (
                <TileLayer
                  url={rvTileUrl}
                  attribution='Weather radar &copy; <a href="https://www.rainviewer.com/">RainViewer</a>'
                  opacity={0.5}
                  zIndex={200}
                />
              )}
              <Polygon
                positions={MASK_POSITIONS}
                pathOptions={{ color: 'none', fillColor: '#000', fillOpacity: 0.6 }}
              />
              {overlayUrl && (
                <ImageOverlay url={overlayUrl} bounds={BOUNDS} opacity={0.82} zIndex={300} />
              )}
              {activePolygons.map((poly, i) => (
                <Polygon key={i} positions={poly.bounds}
                  pathOptions={{ color: poly.color, weight: 2, fillColor: poly.color, fillOpacity: 0.25 }}>
                  <Tooltip>
                    <strong>High Risk Zone</strong><br />
                    Risk: {(poly.risk * 100).toFixed(0)}%
                  </Tooltip>
                </Polygon>
              ))}
            </MapContainer>

            {/* Floating legend */}
            <div className="map-legend">
              {isRainLayer ? <LegendRain /> : <LegendHazard type={activeLayer} />}
            </div>
          </div>

          {/* ── Atmospheric stats ── */}
          {atm.source && (
            <div className="stats-row">
              <StatCard
                icon={Thermometer}
                label="CAPE"
                value={atm.cape?.toFixed(0) ?? '--'}
                unit=" J/kg"
                sub={atm.cape > 2000 ? '🔴 Extreme instability' : atm.cape > 1000 ? '🟡 Active convection' : '🟢 Stable'}
                accentColor="#eab308"
              />
              <StatCard
                icon={Navigation}
                label="Wind"
                value={atm.wind_speed?.toFixed(1) ?? '--'}
                unit=" m/s"
                sub={`${atm.wind_direction?.toFixed(0) ?? '--'}° direction · 10m AGL`}
                accentColor="#38bdf8"
              />
              <StatCard
                icon={Droplets}
                label="Humidity"
                value={atm.humidity?.toFixed(0) ?? '--'}
                unit="%"
                sub={atm.humidity >= 85 ? '🔵 High moisture content' : '⚪ Normal moisture'}
                accentColor="#22d3ee"
              />
              <StatCard
                icon={Cpu}
                label="Model"
                value="U-Net"
                unit=""
                sub={`+ PySTEPS · ${atm.source === 'open-meteo' ? '🟢 Live atm. data' : '🟡 Fallback data'}`}
                accentColor="#a78bfa"
              />
            </div>
          )}
        </main>

        {/* ── RIGHT PANEL: ALERTS ── */}
        <aside className="alerts-panel">
          <div className="alerts-header">
            <AlertTriangle size={14} color="#f87171" />
            <span>Active Alerts</span>
            {alerts.length > 0 && (
              <span className="alert-count">{alerts.length}</span>
            )}
          </div>

          {alerts.length === 0 ? (
            <div className="no-alerts">
              <div className="no-alerts-icon">✅</div>
              <div>No active alerts</div>
              <div className="no-alerts-sub">All hazard thresholds nominal</div>
            </div>
          ) : (
            <div className="alerts-list">
              {alerts.map((alert, i) => <AlertItem key={i} alert={alert} />)}
            </div>
          )}

          {/* Model info footer */}
          <div className="model-info">
            <div className="model-info-row">
              <span className="model-info-label">Architecture</span>
              <span className="model-info-val">UNet + PySTEPS</span>
            </div>
            <div className="model-info-row">
              <span className="model-info-label">Dataset</span>
              <span className="model-info-val">PERSIANN-CCS 4km</span>
            </div>
            <div className="model-info-row">
              <span className="model-info-label">Region</span>
              <span className="model-info-val">Assam, NE India</span>
            </div>
            <div className="model-info-row">
              <span className="model-info-label">Terrain</span>
              <span className="model-info-val">SRTM 1km downscale</span>
            </div>
            {rvTimestamp && (
              <div className="model-info-row">
                <span className="model-info-label">Radar</span>
                <span className="model-info-val">{new Date(rvTimestamp * 1000).toLocaleTimeString()}</span>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
