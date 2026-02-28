//install leaflet, react-leaflet, @types/leaflet.
//run npm install react react-dom leaflet react-leaflet

import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useState } from 'react'

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  .map-app {
    display: flex;
    height: 100vh;
    width: 100vw;
    font-family: 'DM Sans', sans-serif;
    background: #fcfcfc;
  }

  /* ── SIDEBAR ── */
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

  /* ── ROUTE INPUTS ── */
  .route-inputs {
    display: flex;
    flex-direction: column;
    gap: 8px;
    position: relative;
    margin-bottom: 10px;
  }

  .input-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .dot-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
    width: 20px;
    height: 10px;
    flex-shrink: 0;
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .dot.origin { 
    background: #c8f135; }

  .dot.dest { 
    background: #ff5c5c; 
    border: 2px 
    solid #ff5c5c; }

  .dot-line {
    width: 2px;
    height: 5px;
    background: #2e2e2e;
    margin: 10px 0;
  }

  .route-input {
    flex: 1;
    background: #fcfcfc;
    border: 1px solid #111;
    border-radius: 20px;
    padding: 11px 14px;
    color: #e8e8e8;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    font-weight: 400;
    outline: none;
    transition: border-color 0.2s, background 0.2s;
  }

  .route-input::placeholder { color: #555; }

  .route-input:focus {
    border-color: #c8f135;
    background: #878787;
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
    letter-spacing: 0.2px;
    transition: background 0.2s, transform 0.1s;
  }

  .search-btn:hover { background: #6e94f5; }
  .search-btn:active { transform: scale(0.98); }

  /* ── DIVIDER ── */
  .divider {
    height: 1px;
    background: #111;
    margin: 22px 0;
  }

  /* ── DIRECTIONS PANEL ── */
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

  .directions-empty {
    background: #fcfcfc;
    border: 1px dashed #111;
    border-radius: 12px;
    padding: 32px 20px;
    text-align: center;
  }

  /* ── MAP ── */
  .map-container {
    flex: 1;
    position: relative;
  }

  .map-container .leaflet-container {
    width: 100%;
    height: 100%;
  }
`

// Placeholder step data (TODO: replace with real routing API results)
const PLACEHOLDER_STEPS = [
  { instruction: 'Head north on Forbes Ave toward Craig St', detail: '0.2 mi · 1 min' },
  { instruction: 'Turn right onto Craig St', detail: '0.1 mi · 1 min' },
  { instruction: 'Turn left onto Fifth Ave', detail: '1.3 mi · 4 min' },
  { instruction: 'Keep right to stay on Fifth Ave', detail: '0.6 mi · 2 min' },
  { instruction: 'Turn right onto Morewood Ave', detail: '0.3 mi · 1 min' },
  { instruction: 'Arrive at your destination on the right', detail: '—' },
]

export default function Map() {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [steps, setSteps] = useState<typeof PLACEHOLDER_STEPS | null>(null)
  const [searched, setSearched] = useState(false)

  const handleSearch = () => {
    if (!from.trim() || !to.trim()) return

    // TODO: replace with real routing API call
    setSteps(PLACEHOLDER_STEPS)
    setSearched(true)
  }

  return (
    <>
      <style>{styles}</style>
      <div className="map-app">
        {/* ── SIDEBAR ── */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <span className="sidebar-title">Wayfinders</span>
          </div>

          {/* Origin / Destination inputs */}
          <div className="route-inputs">
            <div className="input-row">
              <div className="dot-col">
                <div className="dot origin" />
              </div>
              <input
                className="route-input"
                placeholder="From — starting point"
                value={from}
                onChange={e => setFrom(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <div className="input-row">
              <div className="dot-col">
                <div className="dot dest" />
              </div>
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

          <div className="divider" />

          {/* Directions panel */}
          <div className="directions-header">
            <span className="directions-label">Directions</span>
            {steps && <span className="directions-meta">~9 min · 2.5 mi</span>}
          </div>

          {!searched ? (
            <div className="directions-empty">
              <p className="directions-empty-text">
                Enter a starting point and destination to see turn-by-turn directions here.
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
        </aside>

        {/* ── MAP ── */}
        <div className="map-container">
          <MapContainer
            center={[40.4421676, -79.9959]}
            zoom={13}
            scrollWheelZoom={true}
            style={{ width: '100%', height: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
           {/* marker position is just the "pinpoint" on map */}
            <Marker position={[40.442, -79.9959]}>
              <Popup>Pittsburgh, PA</Popup>
            </Marker>
          </MapContainer>
        </div>
      </div>
    </>
  )
}