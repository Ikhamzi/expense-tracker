export default function MonthSelector({ month, onChange }) {
  return (
    <div className="month-selector">
      <label htmlFor="month">Month</label>
      <input id="month" type="month" value={month} onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}
