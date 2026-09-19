import React from 'react';

export function LegendRain() {
  return (
    <div className="legend-card">
      <div className="legend-title">Rain Rate · mm/hr · IMD Scale</div>
      <div
        className="legend-bar"
        style={{
          background: 'linear-gradient(to right,#000080,#0000ff,#00ffff,#00ff00,#ffff00,#ff7f00,#ff0000)',
        }}
      />
      <div className="legend-labels">
        {['0', '5', '15', '25', '50+'].map((v) => (
          <span key={v}>{v}</span>
        ))}
      </div>
    </div>
  );
}

export function LegendHazard({ type }) {
  const cfgs = {
    cloudburst: { g: 'linear-gradient(to right,#ffffb2,#feb24c,#f03b20,#bd0026)', l: 'Cloudburst Prob.' },
    hail:       { g: 'linear-gradient(to right,#f7fbff,#9ecae1,#3182bd,#08519c)', l: 'Hail Probability' },
    lightning:  { g: 'linear-gradient(to right,#ffffd4,#fe9929,#d95f0e,#993404)', l: 'Lightning Density' },
    downburst:  { g: 'linear-gradient(to right,#fcfbfd,#9e9ac8,#756bb1,#54278f)', l: 'Downburst Risk' },
  };
  const cfg = cfgs[type] ?? cfgs.cloudburst;
  return (
    <div className="legend-card">
      <div className="legend-title">{cfg.l}</div>
      <div className="legend-bar" style={{ background: cfg.g }} />
      <div className="legend-labels">
        <span>Low</span><span>Moderate</span><span>Critical</span>
      </div>
    </div>
  );
}
