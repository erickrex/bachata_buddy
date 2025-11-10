import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// Uncomment to use dynamic CSP injection based on environment
// import { vitePluginCSP } from './vite-plugin-csp.js'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    // Uncomment to enable dynamic CSP injection
    // vitePluginCSP({ environment: mode === 'production' ? 'production' : 'development' })
  ],
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom']
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
}))
