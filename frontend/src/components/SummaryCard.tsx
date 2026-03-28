import type { AnalyzeResponse } from '../api'

interface Props {
  data: AnalyzeResponse
}

const LEVEL_CLASS: Record<string, string> = {
  High: 'badge-high',
  Moderate: 'badge-moderate',
  Low: 'badge-low',
}

export default function SummaryCard({ data }: Props) {
  const { address, risk_profile, summary, violations, complaints, litigations, data_warning } = data
  const badgeClass = LEVEL_CLASS[risk_profile.caution_level] ?? 'badge-low'

  return (
    <div className="summary-card">
      <div className="summary-header">
        <div className="summary-address">
          <span className="address-icon">📍</span>
          <span>
            {address.house_number} {address.street_name},{' '}
            <strong>{address.borough}</strong>
          </span>
        </div>
        <span className={`risk-badge ${badgeClass}`}>{risk_profile.caution_level} Risk</span>
      </div>

      {data_warning && (
        <div className="data-warning">
          ⚠️ Some data sources were unavailable. Results may be incomplete.
        </div>
      )}

      <div className="counts-row">
        <span className="count-item">
          <strong>{violations.length}</strong> violation{violations.length !== 1 ? 's' : ''}
        </span>
        <span className="count-sep">·</span>
        <span className="count-item">
          <strong>{complaints.length}</strong> complaint{complaints.length !== 1 ? 's' : ''}
        </span>
        <span className="count-sep">·</span>
        <span className="count-item">
          <strong>{litigations.length}</strong> litigation{litigations.length !== 1 ? 's' : ''}
        </span>
      </div>

      {risk_profile.reasons.length > 0 && (
        <ul className="reasons-list">
          {risk_profile.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}

      <div className="summary-body">
        {summary.split('\n').map((line, i) =>
          line.trim() ? <p key={i}>{line}</p> : null,
        )}
      </div>
    </div>
  )
}
