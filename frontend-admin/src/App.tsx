import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { ChatProvider } from './contexts/ChatContext'
import { AppRouter } from './components/templates/AppRouter'
import { Toaster } from './components/atoms/Toaster'
import { AIChatBubble } from './components/atoms/AIChatBubble'
import { AIChatModal } from './components/organisms/AIChatModal'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (previously cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/dashboard-admin">
        <ThemeProvider defaultTheme="dark">
          <AuthProvider>
            <ChatProvider>
              <AppRouter />
              <Toaster />
              {/* AI Chat - Always visible */}
              <AIChatBubble />
              <AIChatModal />
            </ChatProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App