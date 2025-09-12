import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Configuração inteligente de Backend URL que funciona em todos os ambientes
function getBackendUrl(): string {
  // 1. Prioridade: variável de ambiente explícita
  if (process.env.VITE_API_URL) {
    return process.env.VITE_API_URL
  }
  
  // 2. Detectar ambiente Docker vs Local
  const isDocker = process.env.DOCKER_ENV === 'true' || process.env.NODE_ENV === 'docker'
  
  if (isDocker) {
    // Em Docker, usar nome do serviço
    return 'http://api-service:8000'
  } else {
    // Desenvolvimento local, usar localhost
    return 'http://localhost:8000'
  }
}

const BACKEND_URL = getBackendUrl()

console.log('🔧 Vite Config: Backend URL =', BACKEND_URL)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3001,
    host: true,
    strictPort: false,
    hmr: {
      clientPort: 3001
    },
    proxy: {
      '/auth': {
        target: BACKEND_URL,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => {
          const newPath = path.replace(/^\/auth/, '/api/v1/auth')
          console.log(`🔄 Proxy: ${path} → ${BACKEND_URL}${newPath}`)
          return newPath
        },
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.error('❌ Proxy error:', err.message)
            console.error('   Request was:', req.url)
            console.error('   Target was:', options.target)
            // Enviar resposta de erro customizada
            if (res && !res.headersSent) {
              res.writeHead(500, {
                'Content-Type': 'application/json',
              })
              res.end(JSON.stringify({ 
                error: 'Proxy error', 
                message: err.message,
                target: options.target 
              }))
            }
          })
          
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log(`➡️  [${new Date().toISOString()}] ${req.method} ${req.url}`)
            console.log(`   Target: ${options.target}${proxyReq.path}`)
          })
          
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log(`⬅️  [${new Date().toISOString()}] ${proxyRes.statusCode} ${req.url}`)
          })
        },
      },
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
        secure: false,
        configure: (proxy, options) => {
          proxy.on('error', (err, _req, res) => {
            console.error('❌ API Proxy error:', err.message)
            if (res && !res.headersSent) {
              res.writeHead(500, {
                'Content-Type': 'application/json',
              })
              res.end(JSON.stringify({ 
                error: 'API Proxy error', 
                message: err.message 
              }))
            }
          })
          
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log(`📡 API: ${req.method} ${req.url} → ${options.target}${proxyReq.path}`)
          })
          
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log(`📊 API Response: ${proxyRes.statusCode} for ${req.url}`)
          })
        },
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  }
})