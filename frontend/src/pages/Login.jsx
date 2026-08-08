import { useEffect, useState } from 'react'
import { api } from '../api.js'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function Login({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' or 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  // Set up the "Sign in with Google" button once the Google script has
  // loaded (it's added via a <script> tag in index.html).
  useEffect(() => {
    if (!window.google || !GOOGLE_CLIENT_ID) return

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        // response.credential is the Google ID token - send it to our
        // backend, which verifies it and gives us back our own JWT.
        try {
          const { access_token } = await api.googleLogin(response.credential)
          onLogin(access_token)
        } catch (err) {
          setError(err.message)
        }
      },
    })

    window.google.accounts.id.renderButton(document.getElementById('google-signin-button'), {
      theme: 'outline',
      size: 'large',
    })
  }, [onLogin])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    try {
      const result =
        mode === 'login' ? await api.login(email, password) : await api.signup(email, password, name)
      onLogin(result.access_token)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="auth-page">
      <h1>Personal Expense Tracker</h1>

      <form onSubmit={handleSubmit} className="auth-form">
        <h2>{mode === 'login' ? 'Log in' : 'Sign up'}</h2>

        {mode === 'signup' && (
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={6}
          required
        />

        {error && <p className="error">{error}</p>}

        <button type="submit">{mode === 'login' ? 'Log in' : 'Sign up'}</button>

        <p className="switch-mode">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            className="link-button"
            onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
          >
            {mode === 'login' ? 'Sign up' : 'Log in'}
          </button>
        </p>
      </form>

      <div className="divider">or</div>

      {/* Google Identity Services renders its own button inside this div */}
      <div id="google-signin-button"></div>
    </div>
  )
}
