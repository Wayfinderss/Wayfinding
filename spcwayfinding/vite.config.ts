import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'https://valhalla1.openstreetmap.de',
        changeOrigin: true,
        // /api/route  → /route
        // /api/height → /height
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})