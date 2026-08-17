import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Mirrors the nginx reverse proxy in the production image, so the client
    // uses the same relative `/api` path in dev and in production. Without
    // this, dev would need an absolute API URL and the two environments would
    // exercise different request paths — and only one of them would be
    // cross-origin, so CORS bugs would show up in production only.
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
