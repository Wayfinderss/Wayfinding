import SPC_LOGO from './assets/SPC_Blk.png'; 
import { useEffect, useRef, useState } from 'react';
import { geocodeAddress } from './services/api';
interface Step {
    instruction: string;
    detail: string;
  }

interface GeocodeResult {
  label: string;
  address: string;
  lat: number;
  lon: number;
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
  
  // const SPC_LOGO = `data:image/png`

// ─────────────────────────────────────────────
//  Styles
// ─────────────────────────────────────────────
  const styles = `
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  
    * { box-sizing: border-box; margin: 0; padding: 0; }
  
    :root {
      --spc-blue: #2e55a5;
      --spc-blue-dark: #1e3c7a;
      --spc-blue-light: #3d6abf;
      --spc-blue-pale: #e8eef8;
      --spc-accent: #c8f135;
    }
 
    .sidebar {
      width: 340px;
      min-width: 340px;
      background: #fcfcfc;
      border-right: 1px solid #111;
      display: flex;
      flex-direction: column;
      gap: 0;
      z-index: 1000;
      height: 100vh;
      overflow: hidden;  /* to make static */
      font-family: 'DM Sans', sans-serif;
    }

    /* ── Blue header banner — logo/title only ── */
    .sidebar-header-banner {
      flex-shrink: 0;
      background: var(--spc-blue);
      padding: 14px 18px;
      border-bottom: 3px solid var(--spc-blue-dark);
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .sidebar-logo {
      height: 34px;
      width: auto;
      filter: brightness(0) invert(1);
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
  
    .sidebar-title-block {
      display: flex;
      flex-direction: column;
    }
  
    .sidebar-title {
      font-size: 15px;
      font-weight: 600;
      color: #ffffff;
      letter-spacing: 0.2px;
      line-height: 1.2;
    }
 
    .sidebar-subtitle {
      font-size: 11px;
      color: rgba(255,255,255,0.65);
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }

    /* ── Inputs + button panel ── */
    .sidebar-inputs-panel {
      flex-shrink: 0;
      background: #fcfcfc;
      border-bottom: 1px solid #d0d9ee;
      padding: 14px 16px;
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
      position: relative;
    }
  
    .input-wrapper {
      flex: 1;
      position: relative;
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

    .suggestions {
      position: absolute;
      top: calc(100% + 2px);
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #111;
      border-radius: 8px;
      list-style: none;
      max-height: 180px;
      overflow-y: auto;
      z-index: 1001;
    }

    .suggestion {
      padding: 10px 14px;
      cursor: pointer;
      border-bottom: 1px solid #eee;
      font-size: 13px;
      color: #111;
    }

    .suggestion:hover { background: #f5f5f5; }
    .suggestion:last-child { border-bottom: none; }
  
    .search-btn {
      width: 100%;
      padding: 12px;
      background: var(--spc-blue);
      border: none;
      border-radius: 10px;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 600;
      color: #ffffff;
      cursor: pointer;
      transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
      box-shadow: 0 2px 8px rgba(46,85,165,0.25);
    }
  
    .search-btn:hover { background: #5a7ee0; }
    .search-btn:active { transform: scale(0.98); }
  
    /* ── Scrollable bottom panel ── */
    .sidebar-scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;       
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
    .status-box.success { background: #e8eef8; color: var(--spc-blue-dark); font-weight: 600; border: 1px solid #b8caeb; }
    .status-box.hint    { background: var(--spc-blue-pale); color: var(--spc-blue); border: 1px solid #c5d3ee; }
  
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
      color: var(--spc-blue);
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
    const [fromSuggestions, setFromSuggestions] = useState<GeocodeResult[]>([]);
    const [toSuggestions, setToSuggestions] = useState<GeocodeResult[]>([]);
    const [showFromSuggestions, setShowFromSuggestions] = useState(false);
    const [showToSuggestions, setShowToSuggestions] = useState(false);
    const fromDebounceRef = useRef<number | null>(null);
    const toDebounceRef = useRef<number | null>(null);

    const handleFromChange = (query: string) => {
      setFrom(query);
      if (fromDebounceRef.current) window.clearTimeout(fromDebounceRef.current);

      if (query.trim().length < 3) {
        setFromSuggestions([]);
        setShowFromSuggestions(false);
        return;
      }

      fromDebounceRef.current = window.setTimeout(async () => {
        try {
          const results = await geocodeAddress(query);
          setFromSuggestions(results);
          setShowFromSuggestions(true);
        } catch {
          setFromSuggestions([]);
          setShowFromSuggestions(false);
        }
      }, 250);
    };

    const handleToChange = (query: string) => {
      setTo(query);
      if (toDebounceRef.current) window.clearTimeout(toDebounceRef.current);

      if (query.trim().length < 3) {
        setToSuggestions([]);
        setShowToSuggestions(false);
        return;
      }

      toDebounceRef.current = window.setTimeout(async () => {
        try {
          const results = await geocodeAddress(query);
          setToSuggestions(results);
          setShowToSuggestions(true);
        } catch {
          setToSuggestions([]);
          setShowToSuggestions(false);
        }
      }, 250);
    };

    const selectFromSuggestion = (suggestion: GeocodeResult) => {
      setFrom(suggestion.label);
      setFromSuggestions([]);
      setShowFromSuggestions(false);
    };

    const selectToSuggestion = (suggestion: GeocodeResult) => {
      setTo(suggestion.label);
      setToSuggestions([]);
      setShowToSuggestions(false);
    };

    useEffect(() => {
      return () => {
        if (fromDebounceRef.current) window.clearTimeout(fromDebounceRef.current);
        if (toDebounceRef.current) window.clearTimeout(toDebounceRef.current);
      };
    }, []);

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
          <div className="sidebar-header-banner">
            <img src={SPC_LOGO} alt="SPC Logo" className="sidebar-logo" />

          {/* <div className="sidebar-sticky"> */}
            <div className="sidebar-title-block">
            {/* <div className="sidebar-header"> */}
              <span className="sidebar-title">Wayfinders</span>
              <span className="sidebar-subtitle">Navigation</span>
            </div>
          </div>

            {/* ── White inputs panel ── */}
          <div className="sidebar-inputs-panel">
            <div className="route-inputs">
              <div className="input-row">
                <div className="dot-col"><div className="dot origin" /></div>
                <div className="input-wrapper">
                  <input
                    className="route-input"
                    placeholder="From — starting point"
                    value={from}
                    onChange={e => handleFromChange(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    onFocus={() => from.length >= 3 && setShowFromSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowFromSuggestions(false), 100)}
                  />
                  {showFromSuggestions && fromSuggestions.length > 0 && (
                    <ul className="suggestions">
                      {fromSuggestions.map((s, i) => (
                        <li key={`${s.label}-${i}`} className="suggestion" onMouseDown={() => selectFromSuggestion(s)}>
                          {s.label}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="input-row">
                <div className="dot-col"><div className="dot dest" /></div>
                <div className="input-wrapper">
                  <input
                    className="route-input"
                    placeholder="To — destination"
                    value={to}
                    onChange={e => handleToChange(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    onFocus={() => to.length >= 3 && setShowToSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowToSuggestions(false), 100)}
                  />
                  {showToSuggestions && toSuggestions.length > 0 && (
                    <ul className="suggestions">
                      {toSuggestions.map((s, i) => (
                        <li key={`${s.label}-${i}`} className="suggestion" onMouseDown={() => selectToSuggestion(s)}>
                          {s.label}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
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