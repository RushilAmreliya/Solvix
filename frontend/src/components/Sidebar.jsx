import React from 'react';
import { Layers, Shield, ChevronRight, Radio } from 'lucide-react';
import { RAIN_LAYERS, HAZARD_LAYERS } from '../constants/weather';

export default function Sidebar({
  activeLayer,
  setActiveLayer,
  data,
  rvDisplayTime,
  rvTileUrl,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-section-label">
          <Layers size={12} /> Precipitation
        </div>
        {RAIN_LAYERS.map((l) => (
          <button
            key={l.key}
            className={`layer-btn${activeLayer === l.key ? ' layer-btn-active' : ''}`}
            style={
              activeLayer === l.key
                ? { borderColor: l.color, background: l.color + '22', color: '#fff' }
                : {}
            }
            onClick={() => setActiveLayer(l.key)}
          >
            <span className="layer-dot" style={{ background: l.color }} />
            <span className="layer-btn-main">{l.label}</span>
            <span className="layer-btn-sub">{l.sublabel}</span>
            {activeLayer === l.key && (
              <ChevronRight size={12} style={{ color: l.color, marginLeft: 'auto' }} />
            )}
          </button>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">
          <Shield size={12} /> Hazard Products
        </div>
        {HAZARD_LAYERS.map(({ key, label, icon: Icon, color }) => (
          <button
            key={key}
            className={`layer-btn${activeLayer === key ? ' layer-btn-active' : ''}`}
            style={
              activeLayer === key
                ? { borderColor: color, background: color + '22', color: '#fff' }
                : {}
            }
            onClick={() => setActiveLayer(key)}
          >
            <Icon size={13} style={{ color: activeLayer === key ? color : '#64748b', flexShrink: 0 }} />
            <span className="layer-btn-main">{label}</span>
            {activeLayer === key && (
              <ChevronRight size={12} style={{ color, marginLeft: 'auto' }} />
            )}
          </button>
        ))}
      </div>

      {/* In-Memory Frame Buffer Status */}
      <div className="buffer-card">
        <div className="buffer-label">
          {data.source === 'live-radar' ? 'Live Radar Buffer' : 'Frame Buffer'}
        </div>
        <div className="buffer-value">{data.buffer_size}</div>
        <div className="buffer-sub">
          {data.source === 'live-radar' ? 'Live sweeps cached' : 'frames cached'}
        </div>
        <div className="buffer-bar">
          <div
            className="buffer-fill"
            style={{
              width: `${Math.min(100, (data.buffer_size / 20) * 100)}%`,
              background:
                data.source === 'live-radar'
                  ? 'linear-gradient(to right, #10b981, #06b6d4)'
                  : undefined,
            }}
          />
        </div>
        <div
          style={{
            marginTop: 6,
            fontSize: 9,
            color: data.source === 'live-radar' ? '#34d399' : '#94a3b8',
            fontWeight: 600,
          }}
        >
          {data.source === 'live-radar' ? '● Real-Time Feed' : '○ Simulation Feed'}
        </div>
      </div>

      {/* RainViewer Live Radar timestamp info */}
      {rvDisplayTime && (
        <div className="rv-info">
          <Radio size={10} color="#34d399" />
          <span>Live radar: {rvDisplayTime}</span>
        </div>
      )}
      {!rvTileUrl && (
        <div className="rv-warn">
          ⚠️ Live radar tiles unavailable — RainViewer fetch pending or network issue. No API key needed.
        </div>
      )}
    </aside>
  );
}
