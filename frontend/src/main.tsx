import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import DeveloperPage from './DeveloperPage.tsx'

const isDeveloper = window.location.pathname.startsWith('/developer')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isDeveloper ? <DeveloperPage /> : <App />}
  </StrictMode>,
)
