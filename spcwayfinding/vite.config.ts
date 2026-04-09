import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/geocode': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
      '/valhalla': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
      '/ways': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
      '/demand': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
    }
  }
})