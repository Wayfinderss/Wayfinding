interface ControlPanelProps {
    startPoint: { lat: number; lon: number } | null;
    endPoint: { lat: number; lon: number } | null;
    isLoading: boolean;
    errorMessage: string | null;
    routePolyline: string | null;
    clearRoute: () => void;
  }
  
  const styles = `
    .control-panel {
      padding: 15px;
      background-color: #f5f5f5;
      border-bottom: 2px solid #ddd;
      display: flex;
      gap: 15px;
      align-items: center;
      flex-wrap: wrap;
      font-family: 'DM Sans', sans-serif;
    }
  
    .control-panel-instructions {
      flex: 1;
      min-width: 200px;
      font-size: 14px;
      color: #333;
    }
  
    .control-panel-clear-btn {
      padding: 10px 20px;
      cursor: pointer;
      background-color: #f44336;
      color: white;
      border: none;
      border-radius: 4px;
      font-weight: bold;
      font-family: 'DM Sans', sans-serif;
      transition: background 0.2s;
    }
  
    .control-panel-clear-btn:hover { background-color: #d32f2f; }
  
    .control-panel-status {
      padding: 10px;
      border-radius: 4px;
      font-size: 13px;
    }
  
    .control-panel-status.loading {
      background-color: #fff3e0;
      color: #e65100;
      font-weight: bold;
    }
  
    .control-panel-status.error {
      background-color: #ffebee;
      color: #c62828;
      border: 1px solid #ef5350;
      flex: 1;
      min-width: 300px;
    }
  
    .control-panel-status.success {
      background-color: #e8f5e9;
      color: #2e7d32;
      font-weight: bold;
    }
  `;
  
  export default function ControlPanel({
    startPoint,
    endPoint,
    isLoading,
    errorMessage,
    routePolyline,
    clearRoute,
  }: ControlPanelProps) {
    return (
      <>
        <style>{styles}</style>
        <div className="control-panel">
          <div className="control-panel-instructions">
            <strong>Instructions: </strong>
            {!startPoint && 'Click on the map to set start point (green marker)'}
            {startPoint && !endPoint && 'Click again to set end point (red marker)'}
            {startPoint && endPoint && 'Route displayed! Click to reset.'}
          </div>
  
          {(startPoint || endPoint) && (
            <button className="control-panel-clear-btn" onClick={clearRoute}>
              Clear Route
            </button>
          )}
  
          {isLoading && (
            <div className="control-panel-status loading">🔄 Finding route...</div>
          )}
  
          {errorMessage && (
            <div className="control-panel-status error">⚠️ {errorMessage}</div>
          )}
  
          {routePolyline && !errorMessage && (
            <div className="control-panel-status success">✓ Route found!</div>
          )}
        </div>
      </>
    );
  }