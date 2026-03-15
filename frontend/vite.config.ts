import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// agrega server.allowedHosts



// https://vite.dev/config/

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
    // Nota: 'allowedHosts' requiere Vite 6 o superior
    allowedHosts: ['api.hptu.org.co'],
  },
});
