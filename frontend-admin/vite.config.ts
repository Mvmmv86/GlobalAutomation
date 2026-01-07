import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Configuração inteligente de Backend URL
function getBackendUrl(mode: string): string {
  const env = loadEnv(mode, process.cwd(), '')
  if (env.VITE_API_URL) {
    return env.VITE_API_URL
  }
  return 'http://localhost:8001'
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const BACKEND_URL = getBackendUrl(mode)
  const isDev = mode === 'development'

  if (isDev) {
    console.log('🔧 Vite Config: Backend URL =', BACKEND_URL)
  }

  return {
    // Em produção, admin está em subdomínio próprio (admin.autonodeia.com), então base = '/'
    base: '/',

    plugins: [
      react({
        // Fast Refresh otimizado
        fastRefresh: true,
      })
    ],

    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },

    // Otimizações de desenvolvimento
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@tanstack/react-query',
        'axios',
        'lucide-react',
        'recharts',
        'date-fns',
        'clsx',
        'tailwind-merge',
      ],
      // Excluir dependências que mudam frequentemente
      exclude: [],
    },

    server: {
      port: 3002,
      host: true,
      strictPort: false,

      // HMR otimizado para WSL
      hmr: {
        overlay: true,
        // Usar polling para WSL (mais confiável)
        // Mas com intervalo maior para não sobrecarregar
      },

      // Watch config otimizado para WSL
      watch: {
        // Usar polling para WSL (sistema de arquivos diferente)
        usePolling: true,
        // Intervalo de polling em ms (maior = menos CPU, mais delay)
        interval: 1000,
        // Ignorar node_modules e outros diretórios grandes
        ignored: [
          '**/node_modules/**',
          '**/.git/**',
          '**/dist/**',
          '**/build/**',
        ],
      },

      proxy: {
        '/auth': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/auth/, '/api/v1/auth'),
        },
        '/api': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        }
      }
    },

    // Configurações de build
    build: {
      outDir: 'dist',
      sourcemap: isDev,
      // Otimizações de bundle
      rollupOptions: {
        output: {
          // Code splitting por vendor
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-ui': ['lucide-react', '@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
            'vendor-charts': ['recharts', 'lightweight-charts'],
            'vendor-utils': ['axios', 'date-fns', 'clsx', 'tailwind-merge', 'zod'],
          },
        },
      },
      // Tamanho máximo de chunk antes de warning
      chunkSizeWarningLimit: 1000,
    },

    // Variáveis de ambiente
    define: {
      __DEV__: isDev,
    },

    // Configurações de esbuild
    esbuild: {
      // Remover console.logs em produção
      drop: isDev ? [] : ['console', 'debugger'],
    },
  }
})
