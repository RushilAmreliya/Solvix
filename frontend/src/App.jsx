import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  MapContainer, TileLayer, ImageOverlay, Polygon, Tooltip,
  CircleMarker, Popup, useMap
} from 'react-leaflet';
import {
  CloudRain, Zap, CloudSnow, Wind, RefreshCcw, Wifi, WifiOff,
  AlertTriangle, Layers, ChevronRight, Activity, Thermometer,
  Droplets, Navigation, Cpu, Shield, Clock, Radio, LocateFixed,
  MapPin, X
} from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import './index.css';

// ── API Config ────────────────────────────────────────────────────────────────
const defaultApiHost =
  typeof window !== 'undefined' && window.location.hostname
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000';
const API_BASE = (import.meta.env.VITE_API_URL || defaultApiHost).replace(/\/$/, '');
const API_URL  = `${API_BASE}/api/v1/forecast/latest`;
const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws/forecast';

// RainViewer v3 public API (free, no key needed)
const RAINVIEWER_API = 'https://api.rainviewer.com/public/weather-maps.json';

const ASSAM_BOUNDS = [[24.0, 89.8], [28.0, 96.0]];
const ASSAM_CENTER = [26.2, 92.9];

// ── WMO weather code → human label ───────────────────────────────────────────
const WMO = {
  0:'Clear sky', 1:'Mainly clear', 2:'Partly cloudy', 3:'Overcast',
  45:'Fog', 48:'Icy fog',
  51:'Light drizzle', 53:'Drizzle', 55:'Heavy drizzle',
  61:'Light rain', 63:'Rain', 65:'Heavy rain',
  71:'Light snow', 73:'Snow', 75:'Heavy snow',
  80:'Showers', 81:'Heavy showers', 82:'Violent showers',
  95:'Thunderstorm', 96:'Thunderstorm + hail', 99:'Heavy thunderstorm',
};
const wmoEmoji = (code) => {
  if (code === 0 || code === 1) return '☀️';
  if (code === 2 || code === 3) return '⛅';
  if (code >= 45 && code <= 48) return '🌫️';
  if (code >= 51 && code <= 67) return '🌧️';
  if (code >= 71 && code <= 77) return '❄️';
  if (code >= 80 && code <= 82) return '🌦️';
  if (code >= 95) return '⛈️';
  return '🌡️';
};

// ── Layer configuration ───────────────────────────────────────────────────────
const RAIN_LAYERS = [
  { key:'current', label:'Now',   sublabel:'Observed',   color:'#3b82f6' },
  { key:'f30',     label:'+30m',  sublabel:'High skill', color:'#22c55e' },
  { key:'f60',     label:'+60m',  sublabel:'High skill', color:'#eab308' },
  { key:'f90',     label:'+90m',  sublabel:'Moderate',   color:'#f97316' },
  { key:'f180',    label:'+3 hr', sublabel:'Outlook',    color:'#ef4444' },
  { key:'f360',    label:'+6 hr', sublabel:'Extended',   color:'#991b1b' },
];

const HAZARD_LAYERS = [
  { key:'cloudburst', label:'Cloudburst', icon:CloudRain,  color:'#ea580c' },
  { key:'hail',       label:'Hail',       icon:CloudSnow,  color:'#2563eb' },
  { key:'lightning',  label:'Lightning',  icon:Zap,        color:'#ca8a04' },
  { key:'downburst',  label:'Downburst',  icon:Wind,       color:'#7c3aed' },
];

// ── Severity config ───────────────────────────────────────────────────────────
const SEVERITY = {
  RED:    { bg:'#450a0a', border:'#dc2626', text:'#f87171', badge:'#dc2626' },
  ORANGE: { bg:'#431407', border:'#ea580c', text:'#fb923c', badge:'#ea580c' },
  YELLOW: { bg:'#422006', border:'#ca8a04', text:'#facc15', badge:'#ca8a04' },
  GREEN:  { bg:'#052e16', border:'#16a34a', text:'#4ade80', badge:'#15803d' },
};

const CONFIDENCE = {
  current:'Observation frame — no model uncertainty',
  f30:    'PySTEPS + U-Net blend · High skill',
  f60:    'PySTEPS + U-Net blend · High skill',
  f90:    'PySTEPS + U-Net blend · Moderate skill',
  f180:   'Advection outlook · Skill degrades past +2 hr',
  f360:   'Extended outlook · Low confidence beyond +2 hr',
};

// ── Map: fly to location ──────────────────────────────────────────────────────
function FlyTo({ target, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, zoom ?? 10, { duration: 1.2 });
  }, [map, target, zoom]);
  return null;
}

function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (map && bounds) map.fitBounds(bounds, { padding:[8,8], animate:false });
  }, [map, bounds]);
  return null;
}

// ── Mask polygon (dims area outside Assam bounding box) ──────────────────────
const MASK_POSITIONS = [
  [[-90,-360],[90,-360],[90,360],[-90,360]],
  [[24.0,89.8],[28.0,89.8],[28.0,96.0],[24.0,96.0]],
];

// ── Legends ───────────────────────────────────────────────────────────────────
function LegendRain() {
  return (
    <div className="legend-card">
      <div className="legend-title">Rain Rate · mm/hr · IMD Scale</div>
      <div className="legend-bar" style={{
        background:'linear-gradient(to right,#000080,#0000ff,#00ffff,#00ff00,#ffff00,#ff7f00,#ff0000)'
      }}/>
      <div className="legend-labels">
        {['0','5','15','25','50+'].map(v=><span key={v}>{v}</span>)}
      </div>
    </div>
  );
}

function LegendHazard({ type }) {
  const cfgs = {
    cloudburst:{ g:'linear-gradient(to right,#ffffb2,#feb24c,#f03b20,#bd0026)', l:'Cloudburst Prob.' },
    hail:      { g:'linear-gradient(to right,#f7fbff,#9ecae1,#3182bd,#08519c)', l:'Hail Probability' },
    lightning: { g:'linear-gradient(to right,#ffffd4,#fe9929,#d95f0e,#993404)', l:'Lightning Density' },
    downburst: { g:'linear-gradient(to right,#fcfbfd,#9e9ac8,#756bb1,#54278f)', l:'Downburst Risk' },
  };
  const cfg = cfgs[type] ?? cfgs.cloudburst;
  return (
    <div className="legend-card">
      <div className="legend-title">{cfg.l}</div>
      <div className="legend-bar" style={{ background:cfg.g }}/>
      <div className="legend-labels">
        <span>Low</span><span>Moderate</span><span>Critical</span>
      </div>
    </div>
  );
}

// ── Alert item ────────────────────────────────────────────────────────────────
function AlertItem({ alert }) {
  const s = SEVERITY[alert.severity] ?? SEVERITY.GREEN;
  const icons = { RED:'🔴', ORANGE:'🟠', YELLOW:'🟡', GREEN:'🟢' };
  return (
    <div className="alert-item" style={{ background:s.bg, borderColor:s.border }}>
      <div className="alert-header">
        <span className="alert-icon">{icons[alert.severity] ?? '🟢'}</span>
        <div className="alert-body">
          <div className="alert-title" style={{ color:s.text }}>{alert.title}</div>
          {alert.reason && <div className="alert-reason">{alert.reason}</div>}
        </div>
        <div className="alert-meta">
          <span className="alert-badge" style={{ background:s.badge }}>{alert.severity}</span>
          {alert.eta_minutes && <span className="alert-eta">ETA {alert.eta_minutes}m</span>}
        </div>
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <div className="skeleton-root">
      <div className="skeleton-header"/>
      <div className="skeleton-body">
        <div className="skeleton-sidebar"/>
        <div className="skeleton-main"/>
      </div>
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ icon:Icon, label, value, unit, sub, accent }) {
  return (
    <div className="stat-card" style={{ borderColor:accent+'44' }}>
      <div className="stat-icon" style={{ color:accent }}><Icon size={18}/></div>
      <div className="stat-content">
        <div className="stat-label" style={{ color:accent }}>{label}</div>
        <div className="stat-value">{value}<span className="stat-unit">{unit}</span></div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  );
}

// ── Local weather popup card (for user's location) ────────────────────────────
function LocationWeatherCard({ weather, address, onClose }) {
  if (!weather) return null;
  const emoji = wmoEmoji(weather.weather_code ?? 0);
  return (
    <div className="loc-card">
      <button className="loc-card-close" onClick={onClose}><X size={13}/></button>
      <div className="loc-card-header">
        <MapPin size={14} color="#60a5fa"/>
        <span className="loc-card-place">{address ?? 'Your Location'}</span>
      </div>
      <div className="loc-card-main">
        <span className="loc-emoji">{emoji}</span>
        <div>
          <div className="loc-temp">{weather.temperature_2m?.toFixed(1) ?? '--'}°C</div>
          <div className="loc-condition">{WMO[weather.weather_code] ?? 'Unknown'}</div>
        </div>
      </div>
      <div className="loc-grid">
        <div className="loc-stat">
          <Droplets size={11} color="#38bdf8"/>
          <span>{weather.relative_humidity_2m?.toFixed(0) ?? '--'}%</span>
          <span className="loc-stat-label">Humidity</span>
        </div>
        <div className="loc-stat">
          <Wind size={11} color="#94a3b8"/>
          <span>{weather.wind_speed_10m?.toFixed(1) ?? '--'} m/s</span>
          <span className="loc-stat-label">Wind</span>
        </div>
        <div className="loc-stat">
          <CloudRain size={11} color="#60a5fa"/>
          <span>{weather.precipitation?.toFixed(1) ?? '0'} mm</span>
          <span className="loc-stat-label">Precip</span>
        </div>
      </div>
      <div className="loc-footer">Live data · Open-Meteo · No API key required</div>
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

  // RainViewer state
  const [rvManifest,     setRvManifest]     = useState(null); // full manifest
  const [rvFrameIdx,     setRvFrameIdx]     = useState(-1);   // index into past frames (-1 = latest)

  // Severity debounce — only update badge after 3 consistent readings
  const [displaySeverity, setDisplaySeverity] = useState('GREEN');
  const severityHistory = useRef([]);

  // User location
  const [userLoc,        setUserLoc]        = useState(null);  // {lat, lng}
  const [localWeather,   setLocalWeather]   = useState(null);
  const [locAddress,     setLocAddress]     = useState(null);
  const [locating,       setLocating]       = useState(false);
  const [flyTarget,      setFlyTarget]      = useState(null);
  const [showLocCard,    setShowLocCard]    = useState(false);
  const [syncingRadar,   setSyncingRadar]   = useState(false);
  const [basemapStyle,   setBasemapStyle]   = useState('dark'); // 'dark' | 'satellite' | 'streets'

  const wsRef = useRef(null);

  // ── Sync Live Radar explicitly ─────────────────────────────────────────────
  const syncLiveRadar = useCallback(async () => {
    setSyncingRadar(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingest/sync-live-radar`, { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        if (json.forecast) {
          setData(json.forecast);
          setLastUpdated(new Date().toLocaleTimeString());
        }
      }
    } catch (e) {
      console.error('Failed to sync live radar:', e);
    } finally {
      setSyncingRadar(false);
    }
  }, []);

  // ── RainViewer v3 manifest fetch ────────────────────────────────────────────
  const fetchRainViewer = useCallback(async () => {
    try {
      const res  = await fetch(RAINVIEWER_API);
      if (!res.ok) return;
      const json = await res.json();
      setRvManifest(json);
      setRvFrameIdx(-1); // always jump to latest on refresh
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchRainViewer();
    const t = setInterval(fetchRainViewer, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [fetchRainViewer]);

  // ── Backend data fetch + WebSocket ─────────────────────────────────────────
  const fetchHttpData = useCallback(async () => {
    try {
      const res  = await fetch(API_URL);
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
    let retryCount = 0;
    const MAX_RETRIES = 20;
    let retryTimer = null;

    const connectWS = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;
        ws.onopen    = () => { setConnectionMode('ws'); setError(null); retryCount = 0; };
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'forecast' && msg.data) {
              setData(msg.data);
              setLastUpdated(new Date().toLocaleTimeString());
              setError(null);
              retryCount = 0;
            } else if (msg.type === 'frame_ingested') {
              fetchHttpData();
            }
          } catch {}
        };
        ws.onerror = () => setConnectionMode('http');
        ws.onclose = () => setConnectionMode(p => p === 'ws' ? 'http' : p);
      } catch { setConnectionMode('http'); }
    };

    const tryFetch = async () => {
      try {
        const res  = await fetch(API_URL, { signal: AbortSignal.timeout(8000) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
        setError(null);
        setLastUpdated(new Date().toLocaleTimeString());
        setConnectionMode(prev => prev === 'ws' ? 'ws' : 'http');
        retryCount = 0;
      } catch (err) {
        const msg = err?.message ?? 'Failed to fetch';
        setError(msg);
        setConnectionMode('error');
        // Auto-retry with backoff up to 20 times while backend is starting up
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          const delay = Math.min(2000 * retryCount, 10000); // 2s, 4s, 6s … max 10s
          retryTimer = setTimeout(tryFetch, delay);
        }
      }
    };

    connectWS();
    retryTimer = setTimeout(tryFetch, 500); // try immediately
    // ─── poll every 30 s after initial load ──
    const t1 = setInterval(fetchHttpData, 30_000);
    return () => {
      if (retryTimer) clearTimeout(retryTimer);
      clearInterval(t1);
      wsRef.current?.close();
    };
  }, [fetchHttpData]);

  // ── Severity debounce: only update after 3 consecutive identical values ─────
  useEffect(() => {
    if (!data) return;
    const alerts  = data.alerts ?? [];
    const current = ['RED','ORANGE','YELLOW','GREEN'].find(s => alerts.some(a => a.severity === s)) ?? 'GREEN';
    const h = severityHistory.current;
    h.push(current);
    if (h.length > 4) h.shift(); // keep last 4
    // Update only if the last 3 readings all agree
    if (h.length >= 3 && h.slice(-3).every(v => v === current)) {
      setDisplaySeverity(current);
    }
  }, [data]);

  // ── Derived: overlay image + polygons ──────────────────────────────────────
  const overlayUrl = useMemo(() => data?.images?.[activeLayer], [data, activeLayer]);

  const activePolygons = useMemo(() => {
    if (!data) return [];
    if (activeLayer === 'cloudburst') return (data.cloudburst_polygons ?? []).map(p => ({ ...p, color:'#ef4444' }));
    if (activeLayer === 'lightning')  return (data.lightning_polygons  ?? []).map(p => ({ ...p, color:'#f59e0b' }));
    return [];
  }, [data, activeLayer]);

  // ── RainViewer tile URL (v3 format — no API key, no broken tile issues) ────
  const rvFrames = rvManifest?.radar?.past ?? [];
  const rvLatestTime = rvFrames.length > 0 ? rvFrames[rvFrames.length - 1].time : null;
  const rvDisplayTime = rvLatestTime ? new Date(rvLatestTime * 1000).toLocaleTimeString() : null;
  // Use the host from the manifest (RainViewer v3 provides it)
  const rvHost = rvManifest?.host ?? 'https://tilecache.rainviewer.com';
  const rvPath = rvFrames.length > 0
    ? rvFrames[rvFrames.length - 1].path   // v3 provides a full path
    : null;
  // Build tile URL: if v3 path exists use it, else fall back to v2 format
  const rvTileUrl = useMemo(() => {
    if (!rvPath) return null;
    // RainViewer v3: host + path + /256/{z}/{x}/{y}/4/1_1.png
    return `${rvHost}${rvPath}/256/{z}/{x}/{y}/4/1_1.png`;
  }, [rvHost, rvPath]);

  // ── User location ──────────────────────────────────────────────────────────
  const locateUser = useCallback(() => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserLoc({ lat, lng });
        setFlyTarget([lat, lng]);
        setShowLocCard(true);
        setLocating(false);

        // Reverse-geocode via OSM Nominatim (free, no key)
        try {
          const gr = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
            { headers: { 'Accept-Language': 'en' } }
          );
          const gj = await gr.json();
          const addr = gj.address;
          setLocAddress(addr?.city ?? addr?.town ?? addr?.village ?? addr?.county ?? 'Your Location');
        } catch { setLocAddress('Your Location'); }

        // Fetch local weather from Open-Meteo (free, no API key)
        try {
          const wr = await fetch(
            `https://api.open-meteo.com/v1/forecast` +
            `?latitude=${lat}&longitude=${lng}` +
            `&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,weather_code` +
            `&wind_speed_unit=ms&timezone=auto`
          );
          const wj = await wr.json();
          setLocalWeather(wj.current ?? null);
        } catch { setLocalWeather(null); }
      },
      (err) => {
        setLocating(false);
        if (err.code === 1) alert('Location permission denied. Please allow location access and try again.');
        else alert('Could not get your location. Try again.');
      },
      { timeout: 10_000, enableHighAccuracy: true }
    );
  }, []);

  // ── Render: Loading / Error ─────────────────────────────────────────────────
  if (!data) {
    return (
      <div className="app-root" style={{ display:'flex', alignItems:'center', justifyContent:'center', background:'#0a0f1a', minHeight:'100vh' }}>
        <div style={{ textAlign:'center', maxWidth:380, padding:32 }}>
          {/* App logo */}
          <div style={{ marginBottom:20, display:'flex', alignItems:'center', justifyContent:'center', gap:10 }}>
            <div style={{ background:'#1e3a5f', borderRadius:12, padding:10 }}>
              <CloudRain size={32} color="#60a5fa"/>
            </div>
            <div style={{ textAlign:'left' }}>
              <div style={{ color:'#f1f5f9', fontWeight:800, fontSize:18 }}>NowCast Fusion</div>
              <div style={{ color:'#64748b', fontSize:12 }}>Convective EWS · NE India (Assam)</div>
            </div>
          </div>

          {error ? (
            <>
              {/* Animated connecting spinner */}
              <div style={{ margin:'24px auto', width:56, height:56, position:'relative' }}>
                <div style={{
                  position:'absolute', inset:0, borderRadius:'50%',
                  border:'3px solid #1e3a5f',
                  borderTopColor:'#3b82f6',
                  animation:'spin 1s linear infinite',
                }}/>
                <Activity size={22} color="#60a5fa" style={{ position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)' }}/>
              </div>
              <div style={{ color:'#94a3b8', fontSize:14, marginBottom:8 }}>Connecting to backend…</div>
              <div style={{ color:'#475569', fontSize:12, marginBottom:24 }}>
                Auto-retrying — this usually takes 5–10 seconds on first start
              </div>
              <div style={{ background:'#1e293b', borderRadius:8, padding:'10px 16px', marginBottom:20, border:'1px solid #334155' }}>
                <div style={{ color:'#64748b', fontSize:11, marginBottom:4 }}>Start the backend if not running:</div>
                <code style={{ color:'#38bdf8', fontSize:11 }}>python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000</code>
              </div>
              <button className="error-btn" onClick={fetchHttpData} style={{ marginRight:8 }}>
                <RefreshCcw size={13}/> Retry Now
              </button>
            </>
          ) : (
            <>
              <div style={{ margin:'24px auto', width:56, height:56, position:'relative' }}>
                <div style={{
                  position:'absolute', inset:0, borderRadius:'50%',
                  border:'3px solid #1e3a5f',
                  borderTopColor:'#3b82f6',
                  animation:'spin 1s linear infinite',
                }}/>
                <Activity size={22} color="#60a5fa" style={{ position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)' }}/>
              </div>
              <div style={{ color:'#94a3b8', fontSize:14 }}>Loading live weather data…</div>
            </>
          )}
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── Derived display values ──────────────────────────────────────────────────
  const alerts         = data.alerts ?? [];
  const worstStyle     = SEVERITY[displaySeverity];
  const atm            = data.atmospheric_context ?? {};
  const isRainLayer    = RAIN_LAYERS.some(l => l.key === activeLayer);
  const activeRainCfg  = RAIN_LAYERS.find(l  => l.key === activeLayer);
  const activeHazCfg   = HAZARD_LAYERS.find(l => l.key === activeLayer);

  const connStatus = {
    ws:         { Icon:Wifi,     label:'Live WebSocket', color:'#4ade80' },
    http:       { Icon:Radio,    label:'Polling 30s',    color:'#facc15' },
    error:      { Icon:WifiOff,  label:'Disconnected',   color:'#f87171' },
    connecting: { Icon:Activity, label:'Connecting…',   color:'#94a3b8' },
  }[connectionMode] ?? { Icon:Activity, label:connectionMode, color:'#94a3b8' };
  const ConnIcon = connStatus.Icon;

  return (
    <div className="app-root">

      {/* ══ HEADER ══════════════════════════════════════════════════════════ */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon-wrap">
            <CloudRain size={22} color="#60a5fa"/>
          </div>
          <div>
            <div className="brand-name">NowCast Fusion</div>
            <div className="brand-sub">Convective EWS · North-East India (Assam)</div>
          </div>
        </div>

        <div className="header-center">
          <div className="severity-pill"
            style={{ background:worstStyle.bg, borderColor:worstStyle.border }}>
            <span className={`sev-dot${displaySeverity==='RED'?' pulse':''}`}
              style={{ background:worstStyle.text }}/>
            <span style={{ color:worstStyle.text, fontWeight:700, fontSize:13 }}>
              {displaySeverity === 'GREEN' ? 'ALL CLEAR' : `${displaySeverity} ALERT`}
            </span>
          </div>
        </div>

        <div className="header-right">
          {/* Sync Live Radar button */}
          <button
            className={`locate-btn${syncingRadar ? ' locating' : ''}`}
            onClick={syncLiveRadar}
            title="Fetch & analyze newest live radar sweep from RainViewer"
            disabled={syncingRadar}
            style={{ background: '#064e3b', borderColor: '#059669', color: '#34d399' }}
          >
            <Radio size={13} className={syncingRadar ? 'pulse' : ''} />
            {syncingRadar ? 'Syncing Radar…' : 'Sync Live Radar'}
          </button>

          {/* Locate-me button */}
          <button
            className={`locate-btn${locating ? ' locating' : ''}`}
            onClick={locateUser}
            title="Get my location & local weather"
            disabled={locating}
          >
            <LocateFixed size={13}/>
            {locating ? 'Locating…' : 'My Location'}
          </button>

          <div className="conn-status" style={{ borderColor: data?.is_live_radar ? '#10b98166' : connStatus.color+'55' }}>
            {data?.is_live_radar ? (
              <>
                <span className="live-dot-anim" style={{ background: '#34d399' }} />
                <span style={{ color: '#34d399', fontSize: 11, fontWeight: 700 }}>LIVE RADAR</span>
              </>
            ) : (
              <>
                <ConnIcon size={13} style={{ color:connStatus.color }}/>
                <span style={{ color:connStatus.color, fontSize: 12 }}>{connStatus.label}</span>
              </>
            )}
          </div>
          {lastUpdated && (
            <div className="update-time">
              <Clock size={11} color="#64748b"/>
              <span>{lastUpdated}</span>
            </div>
          )}
          <button className="refresh-btn" onClick={fetchHttpData} title="Force refresh">
            <RefreshCcw size={14}/>
          </button>
        </div>
      </header>

      {/* ══ BODY ════════════════════════════════════════════════════════════ */}
      <div className="app-body">

        {/* ── LEFT SIDEBAR ── */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-section-label"><Layers size={12}/> Precipitation</div>
            {RAIN_LAYERS.map(l => (
              <button key={l.key}
                className={`layer-btn${activeLayer===l.key?' layer-btn-active':''}`}
                style={activeLayer===l.key
                  ? { borderColor:l.color, background:l.color+'22', color:'#fff' }
                  : {}}
                onClick={() => setActiveLayer(l.key)}>
                <span className="layer-dot" style={{ background:l.color }}/>
                <span className="layer-btn-main">{l.label}</span>
                <span className="layer-btn-sub">{l.sublabel}</span>
                {activeLayer===l.key && <ChevronRight size={12} style={{ color:l.color, marginLeft:'auto' }}/>}
              </button>
            ))}
          </div>

          <div className="sidebar-section">
            <div className="sidebar-section-label"><Shield size={12}/> Hazard Products</div>
            {HAZARD_LAYERS.map(({ key, label, icon:Icon, color }) => (
              <button key={key}
                className={`layer-btn${activeLayer===key?' layer-btn-active':''}`}
                style={activeLayer===key
                  ? { borderColor:color, background:color+'22', color:'#fff' }
                  : {}}
                onClick={() => setActiveLayer(key)}>
                <Icon size={13} style={{ color:activeLayer===key ? color : '#64748b', flexShrink:0 }}/>
                <span className="layer-btn-main">{label}</span>
                {activeLayer===key && <ChevronRight size={12} style={{ color, marginLeft:'auto' }}/>}
              </button>
            ))}
          </div>

          {/* Buffer */}
          <div className="buffer-card">
            <div className="buffer-label">{data.source === 'live-radar' ? 'Live Radar Buffer' : 'Frame Buffer'}</div>
            <div className="buffer-value">{data.buffer_size}</div>
            <div className="buffer-sub">{data.source === 'live-radar' ? 'Live sweeps cached' : 'frames cached'}</div>
            <div className="buffer-bar">
              <div className="buffer-fill"
                style={{ width:`${Math.min(100,(data.buffer_size/20)*100)}%`, background: data.source === 'live-radar' ? 'linear-gradient(to right, #10b981, #06b6d4)' : undefined }}/>
            </div>
            <div style={{ marginTop: 6, fontSize: 9, color: data.source === 'live-radar' ? '#34d399' : '#94a3b8', fontWeight: 600 }}>
              {data.source === 'live-radar' ? '● Real-Time Feed' : '○ Simulation Feed'}
            </div>
          </div>

          {/* RainViewer timestamp info */}
          {rvDisplayTime && (
            <div className="rv-info">
              <Radio size={10} color="#34d399"/>
              <span>Live radar: {rvDisplayTime}</span>
            </div>
          )}
          {!rvTileUrl && (
            <div className="rv-warn">
              ⚠️ Live radar tiles unavailable — RainViewer fetch pending or network issue. No API key needed.
            </div>
          )}
        </aside>

        {/* ── MAIN PANEL ── */}
        <main className="main-panel">
          {/* Map sub-header */}
          <div className="map-header">
            <div className="map-header-left">
              <span className="map-layer-dot"
                style={{ background:isRainLayer ? activeRainCfg?.color : activeHazCfg?.color }}/>
              <span className="map-title">
                {isRainLayer
                  ? `Precipitation · ${activeRainCfg?.label}`
                  : `${activeHazCfg?.label} Risk`}
              </span>
              {data?.is_live_radar ? (
                <span className="live-badge" style={{ background: '#064e3b', borderColor: '#059669', color: '#34d399' }}>
                  <span className="live-dot-anim" style={{ background: '#34d399' }}/> REAL LIVE RADAR
                </span>
              ) : rvTileUrl ? (
                <span className="live-badge">
                  <span className="live-dot-anim"/> LIVE Radar
                </span>
              ) : null}
            </div>
            <div className="map-caveat" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ display: 'flex', background: '#1e293b', borderRadius: 6, padding: 2, gap: 2 }}>
                {[
                  { id: 'dark', label: 'Dark' },
                  { id: 'satellite', label: 'Satellite' },
                  { id: 'streets', label: 'Streets' },
                ].map(b => (
                  <button
                    key={b.id}
                    onClick={() => setBasemapStyle(b.id)}
                    style={{
                      background: basemapStyle === b.id ? '#3b82f6' : 'transparent',
                      color: basemapStyle === b.id ? '#fff' : '#94a3b8',
                      border: 'none',
                      borderRadius: 4,
                      padding: '2px 8px',
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'background 0.15s',
                    }}
                  >
                    {b.label}
                  </button>
                ))}
              </div>
              <span>{isRainLayer ? CONFIDENCE[activeLayer] : 'IMD threshold verified · +30 min lead'}</span>
            </div>
          </div>

          {/* ── Leaflet map ── */}
          <div className="map-wrap">
            <MapContainer
              bounds={ASSAM_BOUNDS}
              boundsOptions={{ padding:[8,8] }}
              maxBounds={ASSAM_BOUNDS}
              maxBoundsViscosity={0.7}
              scrollWheelZoom
              className="map-container"
              style={{ background:'#0f172a' }}
            >
              <FitBounds bounds={ASSAM_BOUNDS}/>
              {flyTarget && <FlyTo target={flyTarget} zoom={10}/>}

              {/* ── Basemap: Clean, 100% Free, Zero Watermark Tiles ── */}
              {basemapStyle === 'dark' && (
                <>
                  <TileLayer
                    key="dark-base"
                    url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
                    subdomains="abcd"
                    maxZoom={19}
                    maxNativeZoom={19}
                  />
                  <TileLayer
                    key="dark-labels"
                    url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png"
                    attribution=""
                    subdomains="abcd"
                    maxZoom={19}
                    maxNativeZoom={19}
                    zIndex={150}
                    pane="shadowPane"
                  />
                </>
              )}

              {basemapStyle === 'satellite' && (
                <>
                  <TileLayer
                    key="sat-base"
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    attribution='&copy; <a href="https://www.esri.com/">Esri</a>, Earthstar Geographics'
                    maxZoom={19}
                    maxNativeZoom={17}
                  />
                  <TileLayer
                    key="sat-labels"
                    url="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                    attribution=""
                    maxZoom={19}
                    maxNativeZoom={17}
                    zIndex={150}
                    pane="shadowPane"
                  />
                </>
              )}

              {basemapStyle === 'streets' && (
                <TileLayer
                  key="streets"
                  url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  maxZoom={19}
                  maxNativeZoom={19}
                />
              )}

              {/* ── RainViewer live radar (free v3 API, no key required) ── */}
              {rvTileUrl && (
                <TileLayer
                  key={rvTileUrl}   /* force remount when URL changes */
                  url={rvTileUrl}
                  attribution='Weather radar &copy; <a href="https://www.rainviewer.com/">RainViewer</a> (free, no API key)'
                  opacity={0.6}
                  zIndex={200}
                />
              )}

              {/* ── Dim mask outside Assam ── */}
              <Polygon
                positions={MASK_POSITIONS}
                pathOptions={{ color:'none', fillColor:'#000', fillOpacity:0.55 }}
              />

              {/* ── Model overlay (from backend) ── */}
              {overlayUrl && (
                <ImageOverlay url={overlayUrl} bounds={ASSAM_BOUNDS} opacity={0.72} zIndex={300}/>
              )}

              {/* ── Hazard polygons ── */}
              {activePolygons.map((poly, i) => (
                <Polygon key={i} positions={poly.bounds}
                  pathOptions={{ color:poly.color, weight:2, fillColor:poly.color, fillOpacity:0.2 }}>
                  <Tooltip><strong>High Risk Zone</strong><br/>Risk: {(poly.risk*100).toFixed(0)}%</Tooltip>
                </Polygon>
              ))}

              {/* ── User location marker ── */}
              {userLoc && (
                <CircleMarker
                  center={[userLoc.lat, userLoc.lng]}
                  radius={10}
                  pathOptions={{ color:'#60a5fa', fillColor:'#3b82f6', fillOpacity:0.9, weight:3 }}
                >
                  <Popup>
                    <div style={{ minWidth:180 }}>
                      <strong style={{ color:'#1e293b' }}>{locAddress ?? 'Your Location'}</strong>
                      {localWeather && (
                        <div style={{ marginTop:6, fontSize:12, color:'#334155' }}>
                          <div>{wmoEmoji(localWeather.weather_code)} {WMO[localWeather.weather_code] ?? ''}</div>
                          <div>🌡️ {localWeather.temperature_2m?.toFixed(1)}°C</div>
                          <div>💧 Humidity: {localWeather.relative_humidity_2m?.toFixed(0)}%</div>
                          <div>💨 Wind: {localWeather.wind_speed_10m?.toFixed(1)} m/s</div>
                          <div>🌧️ Precip: {localWeather.precipitation?.toFixed(1)} mm</div>
                        </div>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              )}
            </MapContainer>

            {/* Legend overlay */}
            <div className="map-legend">
              {isRainLayer ? <LegendRain/> : <LegendHazard type={activeLayer}/>}
            </div>

            {/* Location weather card (floating, outside map) */}
            {showLocCard && localWeather && (
              <div className="loc-card-wrap">
                <LocationWeatherCard
                  weather={localWeather}
                  address={locAddress}
                  onClose={() => setShowLocCard(false)}
                />
              </div>
            )}
          </div>

          {/* ── Atmospheric stats row ── */}
          {atm.source && (
            <div className="stats-row">
              <StatCard icon={Thermometer} label="CAPE"
                value={atm.cape?.toFixed(0) ?? '--'} unit=" J/kg"
                sub={atm.cape>2000 ? '🔴 Extreme instability' : atm.cape>1000 ? '🟡 Active convection' : '🟢 Stable'}
                accent="#eab308"/>
              <StatCard icon={Navigation} label="Wind"
                value={atm.wind_speed?.toFixed(1) ?? '--'} unit=" m/s"
                sub={`${atm.wind_direction?.toFixed(0) ?? '--'}° · 10m AGL`}
                accent="#38bdf8"/>
              <StatCard icon={Droplets} label="Humidity"
                value={atm.humidity?.toFixed(0) ?? '--'} unit="%"
                sub={atm.humidity>=85 ? '🔵 High moisture' : '⚪ Normal moisture'}
                accent="#22d3ee"/>
              <StatCard icon={Cpu} label="Model"
                value="U-Net" unit=""
                sub={`PySTEPS · ${atm.source==='open-meteo' ? '🟢 Live atm.' : '🟡 Cached data'}`}
                accent="#a78bfa"/>
            </div>
          )}
        </main>

        {/* ── RIGHT PANEL: ALERTS ── */}
        <aside className="alerts-panel">
          <div className="alerts-header">
            <AlertTriangle size={14} color="#f87171"/>
            <span>Active Alerts</span>
            {alerts.length > 0 && <span className="alert-count">{alerts.length}</span>}
          </div>

          {alerts.length === 0 ? (
            <div className="no-alerts">
              <div className="no-alerts-icon">✅</div>
              <div>No active alerts</div>
              <div className="no-alerts-sub">All thresholds nominal</div>
            </div>
          ) : (
            <div className="alerts-list">
              {alerts.map((a, i) => <AlertItem key={i} alert={a}/>)}
            </div>
          )}

          <div className="model-info">
            <div className="model-info-row"><span className="model-info-label">Architecture</span><span className="model-info-val">UNet + PySTEPS</span></div>
            <div className="model-info-row"><span className="model-info-label">Dataset</span><span className="model-info-val">PERSIANN-CCS 4km</span></div>
            <div className="model-info-row"><span className="model-info-label">Region</span><span className="model-info-val">Assam, NE India</span></div>
            <div className="model-info-row"><span className="model-info-label">Terrain</span><span className="model-info-val">SRTM 1km downscale</span></div>
            <div className="model-info-row"><span className="model-info-label">Radar tiles</span><span className="model-info-val" style={{color:'#4ade80'}}>Free · No API key</span></div>
            {rvDisplayTime && (
              <div className="model-info-row"><span className="model-info-label">Last radar</span><span className="model-info-val">{rvDisplayTime}</span></div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
