// A small wrapper around fetch() that talks to our FastAPI backend.
// It reads the API URL from an environment variable and automatically
// attaches the saved JWT (if any) to every request.

const API_URL = import.meta.env.VITE_API_URL

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    // FastAPI puts validation/auth errors in a "detail" field.
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed with status ${response.status}`)
  }

  if (response.status === 204) {
    return null
  }
  return response.json()
}

export const api = {
  signup: (email, password, name) =>
    request('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password, name }) }),

  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),

  googleLogin: (idToken) =>
    request('/auth/google', { method: 'POST', body: JSON.stringify({ id_token: idToken }) }),

  listExpenses: (month) => request(`/expenses?month=${encodeURIComponent(month)}`),

  addExpense: (expense) => request('/expenses', { method: 'POST', body: JSON.stringify(expense) }),

  updateExpense: (id, expense) =>
    request(`/expenses/${id}`, { method: 'PUT', body: JSON.stringify(expense) }),

  deleteExpense: (id) => request(`/expenses/${id}`, { method: 'DELETE' }),

  getSummary: (month) => request(`/expenses/summary?month=${encodeURIComponent(month)}`),
}
