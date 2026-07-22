/**
 * ClaimCard.jsx — Atomic claim with grade badge, sources, notes.
 * Expandable to show full source list.
 */
import { useState } from 'react'

const GRADE_CONFIG = {
  confirmed: { badge: 'badge-confirmed', icon: '✓', label: 'Confirmed', color: 'var(--confirmed)' },
  disputed: { badge: 'badge-disputed', icon: '⚡', label: 'Disputed', color: 'var(--disputed)' },
  unverified: { badge: 'badge-unverified', icon: '◯', label: 'Unverified', color: 'var(--unverified)' },
  opinion: { badge: 'badge-opinion', icon: '💬', label: 'Opinion', color: 'var(--opinion)' },
}

const STANCE_ICONS = {
  'reports as fact': '📰',
  disputes: '⚡',
  alleges: '❓',
  opinion: '💬',
}

function SourceChip({ source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="source-chip"
      title={`${source.outlet} — ${source.stance} (${source.lean || 'unknown lean'})`}
    >
      {STANCE_ICONS[source.stance] || '📰'}
      <span>{source.outlet}</span>
      {source.lean && source.lean !== 'unknown' && (
        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>
          [{source.lean}]
        </span>
      )}
      {source.date && (
        <span style={{ color: 'var(--text-muted)' }}>
          {source.date.slice(0, 10)}
        </span>
      )}
    </a>
  )
}

export default function ClaimCard({ claim, lang, translations }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = GRADE_CONFIG[claim.grade] || GRADE_CONFIG.unverified

  const displayText = lang === 'hi' && translations?.claims?.[claim.id]
    ? translations.claims[claim.id]
    : claim.text

  const hasSources = claim.sources && claim.sources.length > 0
  const showSources = expanded ? claim.sources : claim.sources?.slice(0, 3)

  return (
    <div
      id={`claim-${claim.id}`}
      className="card animate-in"
      style={{
        borderLeft: `3px solid ${cfg.color}`,
        padding: 'var(--space-5)',
        marginBottom: 'var(--space-3)',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
        <span
          className={`badge ${cfg.badge}`}
          style={{ flexShrink: 0, marginTop: 2 }}
        >
          {cfg.icon} {cfg.label}
        </span>
        <code style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>
          {claim.id}
        </code>
        {claim.disconfirm_searched && (
          <span
            className="badge"
            style={{
              background: claim.disconfirm_found
                ? 'rgba(16,185,129,0.08)'
                : 'rgba(100,116,139,0.08)',
              color: claim.disconfirm_found ? 'var(--confirmed)' : 'var(--unverified)',
              border: `1px solid ${claim.disconfirm_found ? 'var(--confirmed-border)' : 'var(--unverified-border)'}`,
              fontSize: 10,
              flexShrink: 0,
            }}
            title="Whether opposing sources were searched and found"
          >
            {claim.disconfirm_found ? '⊕ Disconfirm found' : '⊘ No disconfirm found'}
          </span>
        )}
      </div>

      {/* Claim text */}
      <p style={{
        fontSize: 15,
        lineHeight: 1.65,
        color: 'var(--text-primary)',
        marginBottom: 'var(--space-3)',
        fontFamily: lang === 'hi' ? 'sans-serif' : 'var(--font-sans)',
      }}>
        {displayText}
      </p>

      {/* Grade notes */}
      {claim.notes && (
        <p style={{
          fontSize: 12,
          color: 'var(--text-secondary)',
          background: 'var(--bg-elevated)',
          borderRadius: 'var(--radius-sm)',
          padding: 'var(--space-2) var(--space-3)',
          marginBottom: 'var(--space-3)',
          fontStyle: 'italic',
          lineHeight: 1.5,
        }}>
          ℹ {claim.notes}
        </p>
      )}

      {/* Sources */}
      {hasSources && (
        <div>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-2)',
            marginBottom: claim.sources.length > 3 ? 'var(--space-2)' : 0,
          }}>
            {showSources.map((s, i) => (
              <SourceChip key={i} source={s} />
            ))}
          </div>

          {claim.sources.length > 3 && (
            <button
              id={`claim-${claim.id}-expand-btn`}
              onClick={() => setExpanded(!expanded)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-bright)',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                padding: '2px 0',
              }}
            >
              {expanded
                ? '▲ Show fewer sources'
                : `▼ Show ${claim.sources.length - 3} more sources`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
