import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tailwindcss(),
    react()
  ],
  server: {
    allowedHosts: ['compensation-speakers-vegetation-cant.trycloudflare.com', 'remix-correlation-bolt-isp.trycloudflare.com']
  }
})
