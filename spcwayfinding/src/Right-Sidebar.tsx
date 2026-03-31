//implementation of basemap icon might need more work after we add accessiblity features
import { useState } from "react";

// ─────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────
type PanelKey = "legend" | "layer" | null;
 
// ─────────────────────────────────────────────
//  Static data
// ─────────────────────────────────────────────
const LEGEND_ITEMS = [
  {
    color: "#c8f135",
    label: "Start Point",
    desc: "Your chosen origin location",
    icon: "●",
  },
  {
    color: "#ff5c5c",
    label: "End Point",
    desc: "Your chosen destination",
    icon: "●",
  },
  {
    color: "#6e94f5",
    label: "Route",
    desc: "Calculated walking / driving path",
    icon: "─",
  },
// take out if not adding in options for closures and etc
//   {
//     color: "#ffb347",
//     label: "Construction Zone",
//     desc: "Active roadwork — expect delays",
//     icon: "▲",
//   },
];
 
const LAYERS = [
  {
    id: "accessible_routes",
    label: "Accessible Routes",
    desc: "Paths with curb cuts, ramps & smooth surfaces",
    icon: "♿",
    enabled: true,
    badge: "A11Y",
    badgeColor: "#a78bfa",
  },
// take out if not adding in options for closures and etc
//   {
//     id: "construction",
//     label: "Construction Zones",
//     desc: "Live roadwork and temporary path closures",
//     icon: "🚧",
//     enabled: true,
//     badge: "LIVE",
//     badgeColor: "#ffb347",
//   },
  {
    id: "elevation",
    label: "Elevation Profile",
    desc: "Gradient shading — useful for wheelchair users (still need to link this to jack's elevation)", 
    icon: "⛰",
    enabled: false,
    badge: null,
    badgeColor: "",
  },
];
 
// ─────────────────────────────────────────────
//  Icons 
// ─────────────────────────────────────────────
const IconLegend = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="2" y="4" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.9" />
    <rect x="2" y="12" width="6" height="4" rx="1.5" fill="currentColor" opacity="0.5" />
    <line x1="11" y1="7" x2="18" y2="7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <line x1="11" y1="14" x2="16" y2="14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);
 
const IconLayer = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M10 2L18 6.5L10 11L2 6.5L10 2Z" fill="currentColor" opacity="0.9" />
    <path d="M2 10L10 14.5L18 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M2 13.5L10 18L18 13.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
  </svg>
);
 
const IconBasemap = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="2" y="2" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.9" />
    <rect x="11" y="2" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.5" />
    <rect x="2" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.5" />
    <rect x="11" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.9" />
  </svg>
);
 
const IconClose = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <line x1="3" y1="3" x2="13" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <line x1="13" y1="3" x2="3" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────
interface RightSidebarProps {
    onResetBasemap?: () => void;
    showElevation: boolean;
    onToggleElevation: (val: boolean) => void;
  }
  

// ─────────────────────────────────────────────
//  Styles
// ─────────────────────────────────────────────
const styles = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
 
  * { box-sizing: border-box; margin: 0; padding: 0; }
 
  /* ── Icon rail ── */
  .right-rail {
    width: 52px;
    min-width: 52px;
    background: #fcfcfc;
    border-left: 1px solid #111;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px 0;
    gap: 6px;
    z-index: 1001;
    font-family: 'DM Sans', sans-serif;
  }
 
  .rail-btn {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    border: 1px solid transparent;
    background: transparent;
    color: #555;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    padding: 0;
  }
 
  .rail-btn:hover {
    background: #f0f4ff;
    color: #6e94f5;
    border-color: #6e94f5;
  }
 
  .rail-btn.active {
    background: #6e94f5;
    color: #fff;
    border-color: #6e94f5;
  }
 
  .rail-btn-label {
    font-size: 8.5px;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    line-height: 1;
  }
 
  .rail-divider {
    width: 28px;
    height: 1px;
    background: #ddd;
    margin: 4px 0;
  }
 
  /* ── Slide-out panel ── */
  .right-panel {
    width: 0;
    overflow: hidden;
    background: #fcfcfc;
    border-left: 0px solid #111;
    display: flex;
    flex-direction: column;
    z-index: 1000;
    font-family: 'DM Sans', sans-serif;
    transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                border-width 0.25s;
  }
 
  .right-panel.open {
    width: 300px;
    min-width: 300px;
    border-left-width: 1px;
  }
 
  .panel-inner {
    width: 300px;
    min-width: 300px;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
  }
 
  /* ── Panel header ── */
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 16px 14px;
    border-bottom: 1px solid #111;
    flex-shrink: 0;
  }
 
  .panel-title-row {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
 
  .panel-title {
    font-size: 15px;
    font-weight: 600;
    color: #111;
    letter-spacing: -0.2px;
  }
 
  .panel-subtitle {
    font-size: 11px;
    color: #888;
    letter-spacing: 0.2px;
  }
 
  .panel-close {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    border: 1px solid #ddd;
    background: transparent;
    color: #555;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s, color 0.15s;
  }
 
  .panel-close:hover { background: #fee; color: #f44336; border-color: #f44336; }
 
  .panel-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
 
  /* ── A11Y notice banner ── */
  .a11y-banner {
    background: #f0edff;
    border: 1px solid #a78bfa;
    border-radius: 8px;
    padding: 9px 12px;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    color: #4c1d95;
    line-height: 1.45;
  }
 
  .a11y-banner-icon { font-size: 14px; flex-shrink: 0; margin-top: 1px; }
 
  /* ── Legend items ── */
  .legend-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
  }
 
  .legend-item:last-child { border-bottom: none; }
 
  .legend-swatch {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
    margin-top: 1px;
  }
 
  .legend-text { flex: 1; }
  .legend-label { font-size: 13px; font-weight: 500; color: #111; margin-bottom: 2px; }
  .legend-desc { font-size: 11px; color: #888; line-height: 1.4; }
 
  /* ── Layer toggles ── */
  .layer-section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.1px;
    text-transform: uppercase;
    color: #aaa;
    margin-bottom: 2px;
    margin-top: 4px;
  }
 
  .layer-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 10px;
    border-radius: 9px;
    border: 1px solid #eee;
    background: #fff;
    transition: border-color 0.15s, background 0.15s;
    cursor: pointer;
  }
 
  .layer-item:hover { border-color: #6e94f5; background: #f5f7ff; }
  .layer-item.active { border-color: #6e94f5; background: #f0f4ff; }
 
  .layer-icon { font-size: 16px; width: 22px; text-align: center; flex-shrink: 0; }
 
  .layer-text { flex: 1; min-width: 0; }
  .layer-label-row { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
  .layer-name { font-size: 13px; font-weight: 500; color: #111; }
 
  .badge {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 1px 5px;
    border-radius: 4px;
    color: #fff;
    text-transform: uppercase;
  }
 
  .layer-desc { font-size: 11px; color: #888; line-height: 1.35; }
 
  /* ── Toggle switch ── */
  .toggle {
    width: 34px;
    height: 20px;
    border-radius: 10px;
    background: #ddd;
    position: relative;
    flex-shrink: 0;
    transition: background 0.2s;
    cursor: pointer;
    border: none;
    padding: 0;
  }
 
  .toggle.on { background: #6e94f5; }
 
  .toggle-thumb {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.2s;
    pointer-events: none;
  }
 
  .toggle.on .toggle-thumb { transform: translateX(14px); }

`;
 
// ─────────────────────────────────────────────
//  Sub-panels
// ─────────────────────────────────────────────
function LegendPanel() {
  return (
    <div className="panel-body">
      <div className="a11y-banner">
        <span className="a11y-banner-icon">♿</span>
        <span>
          <strong>Accessibility data</strong> "insert message of where our data is linked from (SPC)"
        </span>
      </div>
      {LEGEND_ITEMS.map((item) => (
        <div className="legend-item" key={item.label}>
          <div
            className="legend-swatch"
            style={{ background: item.color + "22", color: item.color }}
          >
            {item.icon}
          </div>
          <div className="legend-text">
            <div className="legend-label">{item.label}</div>
            <div className="legend-desc">{item.desc}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
 
function LayerPanel({
    showElevation,
    onToggleElevation,
  }: {
    showElevation: boolean;
    onToggleElevation: (val: boolean) => void;
  }) {
    const [layers, setLayers] = useState(LAYERS);
  
    const toggle = (id: string) => {
      if (id === "elevation") {
        onToggleElevation(!showElevation);
      } else {
        setLayers((prev) =>
          prev.map((l) => (l.id === id ? { ...l, enabled: !l.enabled } : l))
        );
      }
    };
  
    const layersWithElevation = layers.map(l =>
      l.id === "elevation" ? { ...l, enabled: showElevation } : l
    );
  
    const a11yLayers = layersWithElevation.filter((l) => l.badge === "A11Y");
    const otherLayers = layersWithElevation.filter((l) => l.badge !== "A11Y");

    return (
    <div className="panel-body">
      <div className="a11y-banner">
        <span className="a11y-banner-icon">ℹ️</span>
        <span>Toggle map overlays to show or hide features. Accessibility layers are (fill in later depending on backend).</span>
        {/* idk how we want to do this backend wise but we can change this later  */}
      </div>
 
      <div className="layer-section-label">Accessibility</div>
      {a11yLayers.map((layer) => (
        <div
          key={layer.id}
          className={`layer-item${layer.enabled ? " active" : ""}`}
          onClick={() => toggle(layer.id)}
        >
          <span className="layer-icon">{layer.icon}</span>
          <div className="layer-text">
            <div className="layer-label-row">
              <span className="layer-name">{layer.label}</span>
              {layer.badge && (
                <span
                  className="badge"
                  style={{ background: layer.badgeColor }}
                >
                  {layer.badge}
                </span>
              )}
            </div>
            <div className="layer-desc">{layer.desc}</div>
          </div>
          <button
            className={`toggle${layer.enabled ? " on" : ""}`}
            onClick={(e) => { e.stopPropagation(); toggle(layer.id); }}
            aria-label={`${layer.enabled ? "Disable" : "Enable"} ${layer.label}`}
          >
            <div className="toggle-thumb" />
          </button>
        </div>
      ))}
 
      <div className="layer-section-label" style={{ marginTop: 8 }}>Other Layers</div>
      {otherLayers.map((layer) => (
        <div
          key={layer.id}
          className={`layer-item${layer.enabled ? " active" : ""}`}
          onClick={() => toggle(layer.id)}
        >
          <span className="layer-icon">{layer.icon}</span>
          <div className="layer-text">
            <div className="layer-label-row">
              <span className="layer-name">{layer.label}</span>
              {layer.badge && (
                <span
                  className="badge"
                  style={{ background: layer.badgeColor }}
                >
                  {layer.badge}
                </span>
              )}
            </div>
            <div className="layer-desc">{layer.desc}</div>
          </div>
          <button
            className={`toggle${layer.enabled ? " on" : ""}`}
            onClick={(e) => { e.stopPropagation(); toggle(layer.id); }}
            aria-label={`${layer.enabled ? "Disable" : "Enable"} ${layer.label}`}
          >
            <div className="toggle-thumb" />
          </button>
        </div>
      ))}
    </div>
  );
}
 
// ─────────────────────────────────────────────
//  Main export
// ─────────────────────────────────────────────
const PANEL_META: Record<
  Exclude<PanelKey, null>,
  { title: string; subtitle: string }
> = {
  legend: {
    title: "Map Legend",
    subtitle: "Symbol & colour guide",
  },
  layer: {
    title: "Layers",
    subtitle: "Toggle map overlays",
  },
};
 
export default function RightSidebar({ onResetBasemap, showElevation, onToggleElevation }: RightSidebarProps) {
    const [active, setActive] = useState<PanelKey>(null);
    const [resetFired, setResetFired] = useState(false);  
   
    const open = (key: Exclude<PanelKey, null>) =>
      setActive((prev) => (prev === key ? null : key));
   
    const handleReset = () => {
      setResetFired(true);
      setTimeout(() => setResetFired(false), 400);
      onResetBasemap?.();
    };
   
    const meta = active ? PANEL_META[active] : null;
   
  
  return (
    <>
      <style>{styles}</style>
 
      {/* Sliding panel — rendered before the rail so it grows leftward */}
      <div className={`right-panel${active ? " open" : ""}`} role="complementary" aria-label={meta?.title ?? "Map options"}>
        {active && (
          <div className="panel-inner">
            <div className="panel-header">
              <div className="panel-title-row">
                <span className="panel-title">{meta!.title}</span>
                <span className="panel-subtitle">{meta!.subtitle}</span>
              </div>
              <button
                className="panel-close"
                onClick={() => setActive(null)}
                aria-label="Close panel"
              >
                <IconClose />
              </button>
            </div>
 
            {active === "legend" && <LegendPanel />}
            {active === "layer" && (
            <LayerPanel
                showElevation={showElevation}
                onToggleElevation={onToggleElevation}
            />
            )}          
            </div>
        )}
      </div>
 
      {/* Icon rail */}
      <nav className="right-rail" aria-label="Map tools">
        <button
          className={`rail-btn${active === "legend" ? " active" : ""}`}
          onClick={() => open("legend")}
          aria-label="Legend"
          aria-expanded={active === "legend"}
        >
          <IconLegend />
          <span className="rail-btn-label">Legend</span>
        </button>
 
        <div className="rail-divider" />
 
        <button
          className={`rail-btn${active === "layer" ? " active" : ""}`}
          onClick={() => open("layer")}
          aria-label="Layers"
          aria-expanded={active === "layer"}
        >
          <IconLayer />
          <span className="rail-btn-label">Layers</span>
        </button>
 
        <div className="rail-divider" />
 
        {/* Basemap — direct reset, no panel */}
        <button
          className={`rail-btn reset${resetFired ? " fired" : ""}`}
          onClick={handleReset}
          aria-label="Reset map to original basemap"
          title="Reset basemap"
        >
          <IconBasemap />
          <span className="rail-btn-label">Basemap</span>
        </button>
      </nav>
    </>
  );
}