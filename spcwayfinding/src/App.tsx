import './App.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Map from './Map'
import Admin from './Admin'
import 'leaflet/dist/leaflet.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Map />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App