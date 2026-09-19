import React from 'react';

export default function StatCard({ icon: Icon, label, value, unit, sub, accent }) {
  return (
    <div className="stat-card" style={{ borderColor: accent + '44' }}>
      <div className="stat-icon" style={{ color: accent }}><Icon size={18} /></div>
      <div className="stat-content">
        <div className="stat-label" style={{ color: accent }}>{label}</div>
        <div className="stat-value">{value}<span className="stat-unit">{unit}</span></div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  );
}
