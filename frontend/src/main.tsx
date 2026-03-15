import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider } from './context/AuthContext'
import { PanelConfigProvider } from './context/PanelConfigContext'
import { ToastProvider } from './context/ToastContext'
import AppRouter from './router'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <ToastProvider>
        <PanelConfigProvider>
          <AppRouter />
        </PanelConfigProvider>
      </ToastProvider>
    </AuthProvider>
  </StrictMode>,
)
