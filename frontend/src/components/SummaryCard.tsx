import ReactMarkdown from 'react-markdown'
import type { AnalyzeResponse } from '../api'

interface Props { data: AnalyzeResponse }

const VERDICT_CLASS: Record<string, string> = {
  High:     'verdict-high',
  Moderate: 'verdict-moderate',
  Low:      'verdict-low',
}

export default function SummaryCard({ data }: Props) {
  const { address, risk_profile, summary, violations, complaints, litigations, data_warning } = data
  const verdictClass = VERDICT_CLASS[risk_profile.caution_level] ?? 'verdict-low'

  const vCount = violations.length
  const cCount = complaints.length
  const lCount = litigations.length

  return (
    <div className="summary-card">
      <p className="address-kicker">Building Report · {address.borough}</p>

      <div className="verdict-row">
        <h2 className="summary-address-text">
          {address.house_number} {address.street_name}
        </h2>
        <span className={`risk-verdict ${verdictClass}`}>
          {risk_profile.caution_level} Risk
        </span>
      </div>

      <hr className="summary-rule" />

      <div className="stats-row">
        <div className="stat-item">
          <span className={`stat-number ${vCount > 10 ? 'is-high' : vCount > 3 ? 'is-moderate' : ''}`}>
            {vCount}
          </span>
          <span className="stat-label">Violations</span>
        </div>
        <div className="stat-item">
          <span className={`stat-number ${cCount > 20 ? 'is-high' : cCount > 5 ? 'is-moderate' : ''}`}>
            {cCount}
          </span>
          <span className="stat-label">Complaints</span>
        </div>
        <div className="stat-item">
          <span className={`stat-number ${lCount > 0 ? 'is-moderate' : ''}`}>
            {lCount}
          </span>
          <span className="stat-label">Litigations</span>
        </div>
      </div>

      {risk_profile.reasons.length > 0 && (
        <ul className="reasons-list">
          {risk_profile.reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      )}

      {data_warning && (
        <p className="data-warning">
          ⚠ Some data sources were unavailable — results may be incomplete.
        </p>
      )}

      <hr className="summary-divider" />

      <div className="summary-body">
        <ReactMarkdown>{summary}</ReactMarkdown>
      </div>
    </div>
  )
}
