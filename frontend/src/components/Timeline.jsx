/**
 * Timeline.jsx — Vertical timeline of events with dispute markers and claim links.
 */

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatDate(dateStr) {
  if (!dateStr) return '?'
  try {
    const parts = dateStr.split('-')
    if (parts.length === 3) {
      const d = new Date(dateStr)
      return `${d.getDate()} ${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`
    }
    if (parts.length === 2) return `${MONTH_NAMES[parseInt(parts[1]) - 1]} ${parts[0]}`
    return dateStr
  } catch { return dateStr }
}

export default function Timeline({ events, claims, onClaimClick }) {
  if (!events || !events.length) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 40, marginBottom: 'var(--space-3)' }}>📅</div>
        <p>Timeline will appear after Stage 5 completes</p>
      </div>
    )
  }

  // Build a lookup of claim grades for coloring
  const claimGrades = {}
  claims?.forEach(c => { claimGrades[c.id] = c.grade })

  const gradeColor = (grade) => {
    switch (grade) {
      case 'confirmed': return 'var(--confirmed)'
      case 'disputed': return 'var(--disputed)'
      case 'unverified': return 'var(--unverified)'
      case 'opinion': return 'var(--opinion)'
      default: return 'var(--text-muted)'
    }
  }

  return (
    <div className="timeline-track">
      {events.map((event, i) => (
        <div
          key={i}
          id={`timeline-event-${i}`}
          className={`timeline-item ${event.disputed ? 'disputed' : ''}`}
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div className="card" style={{ padding: 'var(--space-4) var(--space-5)' }}>
            {/* Date + dispute badge */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
              marginBottom: 'var(--space-2)',
            }}>
              <span style={{
                fontSize: 12,
                fontWeight: 700,
                color: 'var(--accent-bright)',
                fontFamily: 'var(--font-mono)',
                background: 'var(--accent-dim)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
              }}>
                {formatDate(event.date)}
              </span>
              {event.disputed && (
                <span className="badge badge-disputed" style={{ fontSize: 10 }}>
                  ⚡ Disputed
                </span>
              )}
            </div>

            {/* Event description */}
            <p style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-primary)', marginBottom: 'var(--space-3)' }}>
              {event.event}
            </p>

            {/* Linked claims */}
            {event.claim_ids && event.claim_ids.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
                {event.claim_ids.map(cid => (
                  <button
                    key={cid}
                    id={`timeline-claim-link-${cid}`}
                    onClick={() => onClaimClick?.([cid])}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                    title={`Go to claim ${cid}`}
                  >
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 2,
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                      color: gradeColor(claimGrades[cid]),
                      background: 'var(--bg-elevated)',
                      border: `1px solid ${gradeColor(claimGrades[cid])}40`,
                      borderRadius: 'var(--radius-sm)',
                      padding: '2px 6px',
                    }}>
                      → {cid}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
