/**
 * React Application Entry Point
 * Industry-Standard Frontend Architecture
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { AppStateProvider } from './contexts/AppStateContext'
import { WebSocketProvider } from './contexts/WebSocketContext'
import './index.css'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

// Render React app
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppStateProvider>
          <WebSocketProvider>
            <App />
          </WebSocketProvider>
        </AppStateProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
