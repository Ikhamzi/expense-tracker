import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import MonthSelector from '../components/MonthSelector.jsx'
import ExpenseForm from '../components/ExpenseForm.jsx'
import ExpenseTable from '../components/ExpenseTable.jsx'
import SummaryPanel from '../components/SummaryPanel.jsx'

// Returns the current month as "YYYY-MM", used as the initial selection.
function currentMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export default function Dashboard({ onLogout }) {
  const [month, setMonth] = useState(currentMonth())
  const [expenses, setExpenses] = useState([])
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [expenseList, summaryData] = await Promise.all([
        api.listExpenses(month),
        api.getSummary(month),
      ])
      setExpenses(expenseList)
      setSummary(summaryData)
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [month])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleAdd(expense) {
    await api.addExpense(expense)
    await loadData()
  }

  async function handleUpdate(id, expense) {
    await api.updateExpense(id, expense)
    await loadData()
  }

  async function handleDelete(id) {
    await api.deleteExpense(id)
    await loadData()
  }

  return (
    <div className="dashboard">
      <header>
        <h1>Expense Tracker</h1>
        <button onClick={onLogout}>Log out</button>
      </header>

      {error && <p className="error">{error}</p>}

      <MonthSelector month={month} onChange={setMonth} />

      <div className="dashboard-grid">
        <div className="dashboard-main">
          <ExpenseForm onAdd={handleAdd} />
          <ExpenseTable expenses={expenses} onUpdate={handleUpdate} onDelete={handleDelete} />
        </div>
        <SummaryPanel summary={summary} />
      </div>
    </div>
  )
}
