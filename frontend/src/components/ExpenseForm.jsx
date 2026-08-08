import { useState } from 'react'

const CATEGORIES = ['Food', 'Transport', 'Housing', 'Entertainment', 'Health', 'Other']

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default function ExpenseForm({ onAdd }) {
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [description, setDescription] = useState('')
  const [date, setDate] = useState(today)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    try {
      await onAdd({ amount: Number(amount), category, description, date })
      // Reset the form but keep the chosen category/date for faster entry.
      setAmount('')
      setDescription('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="expense-form">
      <h3>Add expense</h3>

      <input
        type="number"
        step="0.01"
        min="0.01"
        placeholder="Amount"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
        required
      />

      <select value={category} onChange={(event) => setCategory(event.target.value)}>
        {CATEGORIES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <input
        type="text"
        placeholder="Description (optional)"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
      />

      <input type="date" value={date} onChange={(event) => setDate(event.target.value)} required />

      <button type="submit">Add</button>

      {error && <p className="error">{error}</p>}
    </form>
  )
}
