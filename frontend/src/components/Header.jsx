import React from 'react';
import { CloudRain, Radio, LocateFixed, Wifi, WifiOff, Activity, Clock, RefreshCcw } from 'lucide-react';
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
}) {
  const worstStyle = SEVERITY[displaySeverity] ?? SEVERITY.GREEN;

  const connStatus = {
    ws:         { Icon: Wifi,     label: 'Live WebSocket', color: '#4ade80' },
    http:       { Icon: Radio,    label: 'Polling 30s',    color: '#facc15' },
    error:      { Icon: WifiOff,  label: 'Disconnected',   color: '#f87171' },
    connecting: { Icon: Activity, label: 'Connecting…',    color: '#94a3b8' },
  }[connectionMode] ?? { Icon: Activity, label: connectionMode, color: '#94a3b8' };
  const ConnIcon = connStatus.Icon;

  return (
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
        <div
          className="severity-pill"
          style={{ background: worstStyle.bg, borderColor: worstStyle.border }}
        >
          <span
            className={`sev-dot${displaySeverity === 'RED' ? ' pulse' : ''}`}
            style={{ background: worstStyle.text }}
          />
          <span style={{ color: worstStyle.text, fontWeight: 700, fontSize: 13 }}>
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
          <LocateFixed size={13} />
          {locating ? 'Locating…' : 'My Location'}
        </button>

        <div
          className="conn-status"
          style={{ borderColor: data?.is_live_radar ? '#10b98166' : connStatus.color + '55' }}
        >
          {data?.is_live_radar ? (
            <>
              <span className="live-dot-anim" style={{ background: '#34d399' }} />
              <span style={{ color: '#34d399', fontSize: 11, fontWeight: 700 }}>LIVE RADAR</span>
            </>
          ) : (
            <>
              <ConnIcon size={13} style={{ color: connStatus.color }} />
              <span style={{ color: connStatus.color, fontSize: 12 }}>{connStatus.label}</span>
            </>
          )}
        </div>

        {lastUpdated && (
          <div className="update-time">
            <Clock size={11} color="#64748b" />
            <span>{lastUpdated}</span>
          </div>
        )}

        <button className="refresh-btn" onClick={onRefresh} title="Force refresh">
          <RefreshCcw size={14} />
        </button>
      </div>
    </header>
  );
}
