interface Step {
    instruction: string;
    detail: string;
  }
  
  interface SidebarProps {
    from: string;
    to: string;
    setFrom: (v: string) => void;
    setTo: (v: string) => void;
    handleSearch: () => void;
    steps: Step[] | null;
    searched: boolean;
    isLoading: boolean;
    errorMessage: string | null;
    routePolyline: string | null;
    startPoint: { lat: number; lon: number } | null;
    endPoint: { lat: number; lon: number } | null;
    clearRoute: () => void;
  }
  
  const styles = `
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  
    * { box-sizing: border-box; margin: 0; padding: 0; }
  
    .sidebar {
      width: 340px;
      min-width: 340px;
      background: #fcfcfc;
      border-right: 1px solid #111;
      display: flex;
      flex-direction: column;
      padding: 24px 20px;
      gap: 0;
      z-index: 1000;
      overflow-y: auto;
      font-family: 'DM Sans', sans-serif;
    }

    /* ── Sticky top panel ── */
    .sidebar-sticky {
      flex-shrink: 0;
      padding: 10px 10px 0;
      background: #fcfcfc;
      border-bottom: 1px solid #111;
      padding-bottom: 10px;
    }

    .sidebar-header {
      display: flex;
      align-items: center;
      gap: 5px;
      margin-bottom: 28px;
    }
  
    .sidebar-title {
      font-size: 17px;
      font-weight: 600;
      color: #111;
      letter-spacing: -0.3px;
    }
  
    .route-inputs {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 10px;
    }
  
    .input-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
  
    .dot-col {
      display: flex;
      align-items: center;
      width: 20px;
      flex-shrink: 0;
    }
  
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }
  
    .dot.origin { background: #c8f135; }
    .dot.dest { background: #ff5c5c; }
  
    .route-input {
      flex: 1;
      background: #fcfcfc;
      border: 1px solid #111;
      border-radius: 20px;
      padding: 11px 14px;
      color: #111;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s, background 0.2s;
    }
  
    .route-input::placeholder { color: #555; }
    .route-input:focus { border-color: #c8f135; background: #f5f5f5; }
  
    .search-btn {
      width: 100%;
      margin-top: 16px;
      padding: 12px;
      background: #6e94f5;
      border: none;
      border-radius: 10px;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 600;
      color: #0f0f0f;
      cursor: pointer;
      transition: background 0.2s, transform 0.1s;
    }
  
    .search-btn:hover { background: #5a7ee0; }
    .search-btn:active { transform: scale(0.98); }
  
    /* ── Scrollable bottom panel ── */
    .sidebar-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 10px 10px 14px;
    }

    .divider {
      height: 1px;
      background: #111;
      margin: 22px 0;
    }
  
    .status-box {
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 12px;
    }
    .status-box.loading { background: #fff3e0; color: #e65100; }
    .status-box.error   { background: #ffebee; color: #c62828; border: 1px solid #ef5350; }
    .status-box.success { background: #e8f5e9; color: #2e7d32; font-weight: 600; }
    .status-box.hint    { background: #f0f4ff; color: #3a3a3a; }
  
    .clear-btn {
      width: 100%;
      padding: 8px;
      background: transparent;
      border: 1px solid #f44336;
      border-radius: 8px;
      color: #f44336;
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      margin-bottom: 12px;
      transition: background 0.2s;
    }
    .clear-btn:hover { background: #fff0f0; }
  
    .directions-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
    }
  
    .directions-label {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: #555;
    }
  
    .directions-meta { font-size: 12px; color: #555; }
  
    .directions-empty {
      background: #fcfcfc;
      border: 1px dashed #111;
      border-radius: 12px;
      padding: 32px 20px;
      text-align: center;
    }
  
    .directions-empty-text { font-size: 13px; color: #555; line-height: 1.5; }
  
    .step-list { display: flex; flex-direction: column; }
  
    .step {
      display: flex;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid #eee;
    }
  
    .step-number-col {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      min-width: 24px;
    }
  
    .step-num {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #6e94f5;
      color: white;
      font-size: 11px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  
    .step-connector { flex: 1; width: 2px; background: #ddd; min-height: 10px; }
    .step-body { flex: 1; }
    .step-instruction { font-size: 13px; color: #111; line-height: 1.4; margin-bottom: 3px; }
    .step-detail { font-size: 12px; color: #888; }
  `;
  
  export default function Sidebar({
    from, to, setFrom, setTo, handleSearch,
    steps, searched,
    isLoading, errorMessage, routePolyline,
    startPoint, endPoint, clearRoute,
  }: SidebarProps) {
    const clickHint = !startPoint
      ? 'Or click the map to set a start point'
      : !endPoint
      ? 'Now click the map to set an end point'
      : null;
  
    return (
      <>
        <style>{styles}</style>
        <aside className="sidebar">
 
          {/* ── Fixed top: title + inputs + button ── */}
          <div className="sidebar-sticky">
            <div className="sidebar-header">
              <span className="sidebar-title">Wayfinders</span>
            </div>
 
            <div className="route-inputs">
              <div className="input-row">
                <div className="dot-col"><div className="dot origin" /></div>
                <input
                  className="route-input"
                  placeholder="From — starting point"
                  value={from}
                  onChange={e => setFrom(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <div className="input-row">
                <div className="dot-col"><div className="dot dest" /></div>
                <input
                  className="route-input"
                  placeholder="To — destination"
                  value={to}
                  onChange={e => setTo(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                />
              </div>
            </div>
 
            <button className="search-btn" onClick={handleSearch}>
              Get Directions
            </button>
          </div>
 
          {/* ── Scrollable bottom: status + directions ── */}
          <div className="sidebar-scroll">
            {/* <div className="divider" /> */}
 
            {clickHint && !isLoading && !errorMessage && !routePolyline && (
              <div className="status-box hint">👆 {clickHint}</div>
            )}
            {isLoading && <div className="status-box loading">🔄 Finding route...</div>}
            {errorMessage && <div className="status-box error">⚠️ {errorMessage}</div>}
            {routePolyline && !errorMessage && <div className="status-box success">✓ Route found!</div>}
            {(startPoint || endPoint) && (
              <button className="clear-btn" onClick={clearRoute}>Clear Route</button>
            )}
 
            <div className="directions-header">
              <span className="directions-label">Directions</span>
              {steps && <span className="directions-meta">~9 min · 2.5 mi</span>}
            </div>
 
            {!searched ? (
              <div className="directions-empty">
                <p className="directions-empty-text">
                  Enter a starting point and destination, or click two points on the map, to see turn-by-turn directions here.
                </p>
              </div>
            ) : (
              <div className="step-list">
                {steps!.map((step, i) => (
                  <div className="step" key={i}>
                    <div className="step-number-col">
                      <div className="step-num">{i + 1}</div>
                      <div className="step-connector" />
                    </div>
                    <div className="step-body">
                      <div className="step-instruction">{step.instruction}</div>
                      <div className="step-detail">{step.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
 
        </aside>
      </>
    );
  }