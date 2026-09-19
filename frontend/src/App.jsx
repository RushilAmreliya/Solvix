import React, { useState, useMemo } from 'react';
import { CloudRain, Activity, RefreshCcw } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import './index.css';

import { useForecast } from './hooks/useForecast';
import { useUserLocation } from './hooks/useUserLocation';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MapPanel from './components/MapPanel';
import AlertsPanel from './components/AlertsPanel';

export default function App() {
  const [activeLayer, setActiveLayer] = useState('current');

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

  // ── Loading / Error View ───────────────────────────────────────────────────
  if (!data) {
    return (
      <div
        className="app-root"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0a0f1a',
          minHeight: '100vh',
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: 380, padding: 32 }}>
          <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
            <div style={{ background: '#1e3a5f', borderRadius: 12, padding: 10 }}>
              <CloudRain size={32} color="#60a5fa" />
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: '#f1f5f9', fontWeight: 800, fontSize: 18 }}>NowCast Fusion</div>
              <div style={{ color: '#64748b', fontSize: 12 }}>Convective EWS · NE India (Assam)</div>
            </div>
          </div>

          {error ? (
            <>
              <div style={{ margin: '24px auto', width: 56, height: 56, position: 'relative' }}>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: '50%',
                    border: '3px solid #1e3a5f',
                    borderTopColor: '#3b82f6',
                    animation: 'spin 1s linear infinite',
                  }}
                />
                <Activity
                  size={22}
                  color="#60a5fa"
                  style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}
                />
              </div>
              <div style={{ color: '#94a3b8', fontSize: 14, marginBottom: 8 }}>Connecting to backend…</div>
              <div style={{ color: '#475569', fontSize: 12, marginBottom: 24 }}>
                Auto-retrying — this usually takes 5–10 seconds on first start
              </div>
              <div style={{ background: '#1e293b', borderRadius: 8, padding: '10px 16px', marginBottom: 20, border: '1px solid #334155' }}>
                <div style={{ color: '#64748b', fontSize: 11, marginBottom: 4 }}>Start the backend if not running:</div>
                <code style={{ color: '#38bdf8', fontSize: 11 }}>python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000</code>
              </div>
              <button className="error-btn" onClick={fetchHttpData} style={{ marginRight: 8 }}>
                <RefreshCcw size={13} /> Retry Now
              </button>
            </>
          ) : (
            <>
              <div style={{ margin: '24px auto', width: 56, height: 56, position: 'relative' }}>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: '50%',
                    border: '3px solid #1e3a5f',
                    borderTopColor: '#3b82f6',
                    animation: 'spin 1s linear infinite',
                  }}
                />
                <Activity
                  size={22}
                  color="#60a5fa"
                  style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}
                />
              </div>
              <div style={{ color: '#94a3b8', fontSize: 14 }}>Loading live weather data…</div>
            </>
          )}
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── Main Dashboard View ────────────────────────────────────────────────────
  return (
    <div className="app-root">
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
      />

      <div className="app-body">
        <Sidebar
          activeLayer={activeLayer}
          setActiveLayer={setActiveLayer}
          data={data}
          rvDisplayTime={rvDisplayTime}
          rvTileUrl={rvTileUrl}
        />

        <MapPanel
          data={data}
          activeLayer={activeLayer}
          rvTileUrl={rvTileUrl}
          userLoc={userLoc}
          localWeather={localWeather}
          locAddress={locAddress}
          flyTarget={flyTarget}
          showLocCard={showLocCard}
          setShowLocCard={setShowLocCard}
        />

        <AlertsPanel alerts={data.alerts ?? []} rvDisplayTime={rvDisplayTime} />
      </div>
    </div>
  );
}
