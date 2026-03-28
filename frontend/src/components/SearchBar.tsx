import { useState, type FormEvent } from 'react'

interface Props {
  onSubmit: (query: string) => void
  loading: boolean
}

export default function SearchBar({ onSubmit, loading }: Props) {
  const [value, setValue] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const q = value.trim()
    if (q) onSubmit(q)
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="search-bar">
        <svg className="search-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          className="search-input"
          placeholder="Enter an NYC address, e.g. 123 Main St Brooklyn"
          value={value}
          onChange={e => setValue(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <button type="submit" className="search-btn" disabled={loading || !value.trim()}>
          {loading ? <span className="btn-spinner" /> : 'Analyze'}
        </button>
      </div>
    </form>
  )
}
