// import React from "react";
import { MapContainer, TileLayer, useMap, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

//install leaflet, react-leaflet, @types/leaflet.

export default function Map() {
  return (
    <MapContainer center={[40.4421676, -79.9959]} zoom={13} scrollWheelZoom={false}>
        <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={[40.442, -79.9959]}>
        <Popup>
          This is a popup of random coordinates
        </Popup>
      </Marker>
    </MapContainer>
  )
}
