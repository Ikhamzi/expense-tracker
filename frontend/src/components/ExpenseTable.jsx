import { useState } from 'react'

export default function ExpenseTable({ expenses, onUpdate, onDelete }) {
  const [editingId, setEditingId] = useState(null)

  if (expenses.length === 0) {
    return <p className="empty-state">No expenses for this month yet.</p>
  }

  return (
    <table className="expense-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Category</th>
          <th>Description</th>
          <th>Amount</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {expenses.map((expense) =>
          editingId === expense.id ? (
            <EditableRow
              key={expense.id}
              expense={expense}
              onCancel={() => setEditingId(null)}
              onSave={async (updated) => {
                await onUpdate(expense.id, updated)
                setEditingId(null)
              }}
            />
          ) : (
            <tr key={expense.id}>
              <td>{expense.date}</td>
              <td>{expense.category}</td>
              <td>{expense.description}</td>
              <td>${Number(expense.amount).toFixed(2)}</td>
              <td className="row-actions">
                <button onClick={() => setEditingId(expense.id)}>Edit</button>
                <button onClick={() => onDelete(expense.id)}>Delete</button>
              </td>
            </tr>
          ),
        )}
      </tbody>
    </table>
  )
}

function EditableRow({ expense, onSave, onCancel }) {
  const [amount, setAmount] = useState(expense.amount)
  const [category, setCategory] = useState(expense.category)
  const [description, setDescription] = useState(expense.description || '')
  const [date, setDate] = useState(expense.date)

  return (
    <tr>
      <td>
        <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
      </td>
      <td>
        <input type="text" value={category} onChange={(event) => setCategory(event.target.value)} />
      </td>
      <td>
        <input
          type="text"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </td>
      <td>
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
      </td>
      <td className="row-actions">
        <button onClick={() => onSave({ amount: Number(amount), category, description, date })}>
          Save
        </button>
        <button onClick={onCancel}>Cancel</button>
      </td>
    </tr>
  )
}
