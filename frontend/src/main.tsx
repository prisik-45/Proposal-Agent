import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App.tsx'
import './index.css'

// Set the base URL for the backend API deployed on Render
axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'https://proposal-agent-oisv.onrender.com'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
