import { useState, useEffect, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

type RebuildStatus = { running: boolean; last_error: string | null }
type LookupResult = { object_id: number; way_id: number } | null

export default function Admin() {
  const [apiKey, setApiKey] = useState('')
  const [tab, setTab] = useState<'lookup' | 'add' | 'update' | 'delete' | 'rebuild'>('lookup')

  // Lookup
  const [lookupId, setLookupId] = useState('')
  const [lookupResult, setLookupResult] = useState<LookupResult>(null)
  const [lookupError, setLookupError] = useState('')

  // Add
  const [addJson, setAddJson] = useState('')
  const [addMsg, setAddMsg] = useState('')
  const [addError, setAddError] = useState('')

  // Update
  const [updateJson, setUpdateJson] = useState('')
  const [updateMsg, setUpdateMsg] = useState('')
  const [updateError, setUpdateError] = useState('')

  // Delete
  const [deleteId, setDeleteId] = useState('')
  const [deleteMsg, setDeleteMsg] = useState('')
  const [deleteError, setDeleteError] = useState('')

  // Rebuild
  const [rebuildMsg, setRebuildMsg] = useState('')
  const [rebuildError, setRebuildError] = useState('')

  // Status polling
  const [status, setStatus] = useState<RebuildStatus | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/ways/status`, {
          headers: { 'x-api-key': apiKey },
        })
        if (res.ok) setStatus(await res.json())
      } catch {}
    }
    poll()
    pollRef.current = setInterval(poll, 5000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [apiKey])

  const headers = { 'Content-Type': 'application/json', 'x-api-key': apiKey }

  const handleLookup = async () => {
    setLookupResult(null)
    setLookupError('')
    try {
      const res = await fetch(`${API_BASE}/ways/${lookupId}`, { headers })
      const data = await res.json()
      if (!res.ok) setLookupError(data.detail ?? 'Not found')
      else setLookupResult(data)
    } catch (e) {
      setLookupError('Request failed')
    }
  }

  const parseFeature = (raw: string): object | null => {
    try { return JSON.parse(raw) } catch { return null }
  }

  const handleAdd = async () => {
    setAddMsg('')
    setAddError('')
    const feature = parseFeature(addJson)
    if (!feature) { setAddError('Invalid JSON'); return }
    try {
      const res = await fetch(`${API_BASE}/ways/`, {
        method: 'POST', headers, body: JSON.stringify(feature),
      })
      const data = await res.json()
      if (!res.ok) setAddError(data.detail ?? 'Error')
      else setAddMsg('Accepted — tile rebuild queued')
    } catch (e) { setAddError(e instanceof Error ? e.message : 'Request failed') }
  }

  const handleUpdate = async () => {
    setUpdateMsg('')
    setUpdateError('')
    const feature = parseFeature(updateJson)
    if (!feature) { setUpdateError('Invalid JSON'); return }
    try {
      const res = await fetch(`${API_BASE}/ways/`, {
        method: 'PUT', headers, body: JSON.stringify(feature),
      })
      const data = await res.json()
      if (!res.ok) setUpdateError(data.detail ?? 'Error')
      else setUpdateMsg(`Accepted — tile rebuild queued (object_id: ${data.object_id})`)
    } catch (e) { setUpdateError(e instanceof Error ? e.message : 'Request failed') }
  }

  const handleDelete = async () => {
    setDeleteMsg('')
    setDeleteError('')
    if (!deleteId) { setDeleteError('Enter an OBJECTID'); return }
    try {
      const res = await fetch(`${API_BASE}/ways/${deleteId}`, {
        method: 'DELETE', headers,
      })
      const data = await res.json()
      if (!res.ok) setDeleteError(data.detail ?? 'Error')
      else setDeleteMsg(`Accepted — way ${deleteId} queued for deletion`)
    } catch (e) { setDeleteError(e instanceof Error ? e.message : 'Request failed') }
  }

  const handleRebuild = async () => {
    setRebuildMsg('')
    setRebuildError('')
    try {
      const res = await fetch(`${API_BASE}/ways/rebuild`, {
        method: 'POST', headers,
      })
      const data = await res.json()
      if (!res.ok) setRebuildError(data.detail ?? 'Error')
      else setRebuildMsg('Rebuild queued')
    } catch (e) { setRebuildError(e instanceof Error ? e.message : 'Request failed') }
  }

  const tabStyle = (t: string) => ({
    padding: '8px 16px',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    borderBottom: tab === t ? '2px solid #0066cc' : '2px solid transparent',
    color: tab === t ? '#0066cc' : '#555',
  } as React.CSSProperties)

  return (
    <div style={{ maxWidth: 720, margin: '40px auto', fontFamily: 'sans-serif', padding: '0 16px' }}>
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>Wayfinder Admin</h1>

      {/* Status bar */}
      <div style={{
        padding: '8px 12px', borderRadius: 6, marginBottom: 24,
        background: status?.running ? '#fff3cd' : status?.last_error ? '#f8d7da' : '#d4edda',
        color: status?.running ? '#856404' : status?.last_error ? '#721c24' : '#155724',
        fontSize: 13,
      }}>
        {status === null
          ? 'Loading status…'
          : status.running
          ? '⏳ Tile rebuild in progress…'
          : status.last_error
          ? `❌ Last rebuild failed: ${status.last_error}`
          : '✓ Tiles up to date'}
      </div>

      {/* API key */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600, fontSize: 13 }}>
          Admin API Key
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={e => setApiKey(e.target.value)}
          placeholder="x-api-key"
          style={{ width: '100%', padding: '8px 10px', borderRadius: 4, border: '1px solid #ccc', fontSize: 14 }}
        />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #ddd', marginBottom: 24 }}>
        {(['lookup', 'add', 'update', 'delete', 'rebuild'] as const).map(t => (
          <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Lookup */}
      {tab === 'lookup' && (
        <Section title="Lookup Way by OBJECTID">
          <Row>
            <input
              value={lookupId}
              onChange={e => setLookupId(e.target.value)}
              placeholder="OBJECTID"
              style={inputStyle}
            />
            <Btn onClick={handleLookup}>Lookup</Btn>
          </Row>
          {lookupResult && (
            <pre style={preStyle}>
              {JSON.stringify(lookupResult, null, 2)}
            </pre>
          )}
          {lookupError && <Err>{lookupError}</Err>}
        </Section>
      )}

      {/* Add */}
      {tab === 'add' && (
        <Section title="Add Way">
          <p style={hintStyle}>Paste a GeoJSON Feature with OBJECTID in properties.</p>
          <textarea
            value={addJson}
            onChange={e => setAddJson(e.target.value)}
            placeholder='{ "type": "Feature", "properties": { "OBJECTID": 123, ... }, "geometry": { ... } }'
            style={textareaStyle}
          />
          <Btn onClick={handleAdd}>Add Way</Btn>
          {addMsg && <Ok>{addMsg}</Ok>}
          {addError && <Err>{addError}</Err>}
        </Section>
      )}

      {/* Update */}
      {tab === 'update' && (
        <Section title="Update Way">
          <p style={hintStyle}>Paste the updated GeoJSON Feature. OBJECTID must be in properties.</p>
          <textarea
            value={updateJson}
            onChange={e => setUpdateJson(e.target.value)}
            placeholder='{ "type": "Feature", "properties": { "OBJECTID": 123, ... }, "geometry": { ... } }'
            style={textareaStyle}
          />
          <Btn onClick={handleUpdate}>Update Way</Btn>
          {updateMsg && <Ok>{updateMsg}</Ok>}
          {updateError && <Err>{updateError}</Err>}
        </Section>
      )}

      {/* Delete */}
      {tab === 'delete' && (
        <Section title="Delete Way">
          <p style={hintStyle}>Enter the OBJECTID of the way to remove from the network.</p>
          <Row>
            <input
              value={deleteId}
              onChange={e => setDeleteId(e.target.value)}
              placeholder="OBJECTID"
              style={inputStyle}
            />
            <Btn onClick={handleDelete} danger>Delete Way</Btn>
          </Row>
          {deleteMsg && <Ok>{deleteMsg}</Ok>}
          {deleteError && <Err>{deleteError}</Err>}
        </Section>
      )}

      {/* Rebuild */}
      {tab === 'rebuild' && (
        <Section title="Rebuild Tiles">
          <p style={hintStyle}>
            Trigger a full tile rebuild from the current network PBF without making any OSM changes.
            This takes ~2 minutes. Routing stays live during the rebuild.
          </p>
          <Btn onClick={handleRebuild}>Trigger Rebuild</Btn>
          {rebuildMsg && <Ok>{rebuildMsg}</Ok>}
          {rebuildError && <Err>{rebuildError}</Err>}
        </Section>
      )}
    </div>
  )
}

// --- Small helpers ---

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 style={{ fontSize: 16, marginBottom: 12 }}>{title}</h2>
      {children}
    </div>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>{children}</div>
}

function Btn({ onClick, children, danger }: { onClick: () => void; children: React.ReactNode; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 16px', borderRadius: 4, border: 'none', cursor: 'pointer',
        background: danger ? '#dc3545' : '#0066cc', color: '#fff', fontWeight: 600, fontSize: 14,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  )
}

function Err({ children }: { children: React.ReactNode }) {
  return <p style={{ color: '#dc3545', marginTop: 8, fontSize: 13 }}>{children}</p>
}

function Ok({ children }: { children: React.ReactNode }) {
  return <p style={{ color: '#155724', marginTop: 8, fontSize: 13 }}>{children}</p>
}

const inputStyle: React.CSSProperties = {
  flex: 1, padding: '8px 10px', borderRadius: 4, border: '1px solid #ccc', fontSize: 14,
}

const textareaStyle: React.CSSProperties = {
  width: '100%', minHeight: 200, padding: '8px 10px', borderRadius: 4,
  border: '1px solid #ccc', fontSize: 13, fontFamily: 'monospace',
  marginBottom: 12, resize: 'vertical', boxSizing: 'border-box',
}

const preStyle: React.CSSProperties = {
  background: '#f4f4f4', padding: 12, borderRadius: 4, fontSize: 13,
  fontFamily: 'monospace', marginTop: 8, overflowX: 'auto',
}

const hintStyle: React.CSSProperties = {
  fontSize: 13, color: '#555', marginBottom: 12,
}