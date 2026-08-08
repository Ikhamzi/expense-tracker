export default function SummaryPanel({ summary }) {
  if (!summary) return null

  return (
    <div className="summary-panel">
      <h3>Summary for {summary.month}</h3>
      <p className="summary-total">Total: ${Number(summary.total).toFixed(2)}</p>

      {summary.by_category.length === 0 ? (
        <p className="empty-state">Nothing to break down yet.</p>
      ) : (
        <ul className="category-breakdown">
          {summary.by_category.map((entry) => (
            <li key={entry.category}>
              <span>{entry.category}</span>
              <span>${Number(entry.total).toFixed(2)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
