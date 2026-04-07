import { useState, useRef, useEffect } from 'react';

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
  onRouteSelect: (route: any) => void;
}

const API_BASE = "http://localhost:8000";

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

  .sidebar-header {
    display: flex;
    align-items: center;
    gap: 10px;
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

  .input-wrapper {
    flex: 1;
    position: relative;
  }

  .route-input {
    width: 100%;
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
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #111;
    border-top: none;
    border-radius: 0 0 12px 12px;
    list-style: none;
    max-height: 180px;
    overflow-y: auto;
    z-index: 1001;
    margin-top: -2px;
  }

  .suggestion {
    padding: 10px 14px;
    cursor: pointer;
    border-bottom: 1px solid #eee;
    font-size: 13px;
    color: #111;
  }

  .suggestion:hover {
    background: #f5f5f5;
  }

  .suggestion:last-child {
    border-bottom: none;
  }

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
  .search-btn:disabled { opacity: 0.6; cursor: not-allowed; }

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
  startPoint, endPoint, clearRoute, onRouteSelect,
}: SidebarProps) {
  const [fromSuggestions, setFromSuggestions] = useState<GeocodeResult[]>([]);
  const [toSuggestions, setToSuggestions] = useState<GeocodeResult[]>([]);
  const [showFromSuggestions, setShowFromSuggestions] = useState(false);
  const [showToSuggestions, setShowToSuggestions] = useState(false);
  const debounceTimer = useRef<NodeJS.Timeout>();

  // Handle "From" input with debounce
  const handleFromChange = (query: string) => {
    setFrom(query);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    
    if (query.length < 3) {
      setFromSuggestions([]);
      setShowFromSuggestions(false);
      return;
    }

    debounceTimer.current = setTimeout(() => {
      fetch(`${API_BASE}/geocode/autocomplete?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          setFromSuggestions(data.results || []);
          setShowFromSuggestions(true);
        })
        .catch(console.error);
    }, 300);
  };

  // Handle "To" input with debounce
  const handleToChange = (query: string) => {
    setTo(query);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    
    if (query.length < 3) {
      setToSuggestions([]);
      setShowToSuggestions(false);
      return;
    }

    debounceTimer.current = setTimeout(() => {
      fetch(`${API_BASE}/geocode/autocomplete?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          setToSuggestions(data.results || []);
          setShowToSuggestions(true);
        })
        .catch(console.error);
    }, 300);
  };

  // Select a suggestion
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

  const clickHint = !startPoint
    ? 'Or click the map to set a start point'
    : !endPoint
    ? 'Now click the map to set an end point'
    : null;

  return (
    <>
      <style>{styles}</style>
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="sidebar-title">Wayfinders</span>
        </div>

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
              />
              {showFromSuggestions && fromSuggestions.length > 0 && (
                <ul className="suggestions">
                  {fromSuggestions.map((s, i) => (
                    <li key={i} className="suggestion" onClick={() => selectFromSuggestion(s)}>
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
              />
              {showToSuggestions && toSuggestions.length > 0 && (
                <ul className="suggestions">
                  {toSuggestions.map((s, i) => (
                    <li key={i} className="suggestion" onClick={() => selectToSuggestion(s)}>
                      {s.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        <button className="search-btn" onClick={handleSearch} disabled={isLoading}>
          {isLoading ? 'Finding route...' : 'Get Directions'}
        </button>

        <div className="divider" />

        {/* Status messages */}
        {clickHint && !isLoading && !errorMessage && !routePolyline && (
          <div className="status-box hint">👆 {clickHint}</div>
        )}
        {isLoading && <div className="status-box loading">🔄 Finding route...</div>}
        {errorMessage && <div className="status-box error">⚠️ {errorMessage}</div>}
        {routePolyline && !errorMessage && <div className="status-box success">✓ Route found!</div>}
        {(startPoint || endPoint) && (
          <button className="clear-btn" onClick={clearRoute}>Clear Route</button>
        )}

        {/* Directions */}
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
        ) : steps ? (
          <div className="step-list">
            {steps.map((step, i) => (
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
        ) : (
          <div className="directions-empty">
            <p className="directions-empty-text">Loading directions...</p>
          </div>
        )}
      </aside>
    </>
  );
}