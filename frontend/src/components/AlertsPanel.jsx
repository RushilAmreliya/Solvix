import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { SEVERITY } from '../constants/weather';

function AlertItem({ alert }) {
  const s = SEVERITY[alert.severity] ?? SEVERITY.GREEN;
  const icons = { RED: '🔴', ORANGE: '🟠', YELLOW: '🟡', GREEN: '🟢' };

  return (
    <div className="alert-item" style={{ background: s.bg, borderColor: s.border }}>
      <div className="alert-header">
        <span className="alert-icon">{icons[alert.severity] ?? '🟢'}</span>
        <div className="alert-body">
          <div className="alert-title" style={{ color: s.text }}>{alert.title}</div>
          {alert.reason && <div className="alert-reason">{alert.reason}</div>}
        </div>
        <div className="alert-meta">
          <span className="alert-badge" style={{ background: s.badge }}>{alert.severity}</span>
          {alert.eta_minutes && <span className="alert-eta">ETA {alert.eta_minutes}m</span>}
        </div>
      </div>
    </div>
  );
}

export default function AlertsPanel({ alerts, rvDisplayTime }) {
  return (
    <aside className="alerts-panel">
      <div className="alerts-header">
        <AlertTriangle size={14} color="#f87171" />
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
          {alerts.map((a, i) => (
            <AlertItem key={i} alert={a} />
          ))}
        </div>
      )}

      <div className="model-info">
        <div className="model-info-row">
          <span className="model-info-label">Architecture</span>
          <span className="model-info-val">UNet + ConvLSTM + PySTEPS</span>
        </div>
        <div className="model-info-row">
          <span className="model-info-label">Dataset</span>
          <span className="model-info-val">PERSIANN-CCS 4km Multi-Year</span>
        </div>
        <div className="model-info-row">
          <span className="model-info-label">Region</span>
          <span className="model-info-val">Assam, NE India</span>
        </div>
        <div className="model-info-row">
          <span className="model-info-label">Terrain</span>
          <span className="model-info-val">SRTM 1km downscale</span>
        </div>
        <div className="model-info-row">
          <span className="model-info-label">Radar tiles</span>
          <span className="model-info-val" style={{ color: '#4ade80' }}>Free · No API key</span>
        </div>
        {rvDisplayTime && (
          <div className="model-info-row">
            <span className="model-info-label">Last radar</span>
            <span className="model-info-val">{rvDisplayTime}</span>
          </div>
        )}
      </div>
    </aside>
  );
}
