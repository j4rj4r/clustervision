import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(process.env.VITE_APP_VERSION ?? 'dev'),
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (['react', 'react-dom', 'react-router-dom'].some((m) => id.includes(`/node_modules/${m}/`))) return 'vendor-react'
          if (['@tanstack/react-query', 'zustand'].some((m) => id.includes(`/node_modules/${m}/`))) return 'vendor-query'
          if (['lucide-react', 'react-hot-toast'].some((m) => id.includes(`/node_modules/${m}/`))) return 'vendor-ui'
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
