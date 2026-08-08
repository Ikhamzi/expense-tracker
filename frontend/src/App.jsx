import { useState } from 'react'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'

export default function App() {
  // If a token is already saved from a previous visit, start logged in.
  const [token, setToken] = useState(() => localStorage.getItem('token'))

  function handleLogin(newToken) {
    localStorage.setItem('token', newToken)
    setToken(newToken)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    setToken(null)
  }

  return token ? <Dashboard onLogout={handleLogout} /> : <Login onLogin={handleLogin} />
}
