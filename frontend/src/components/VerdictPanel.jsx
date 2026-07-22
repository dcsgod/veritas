/**
 * VerdictPanel.jsx — Final verdict summary: confirmed / disputed / unverifiable / opinion.
 * Evidence-only summary. No judgment on cause legitimacy.
 */

const GRADE_CONFIGS = {
  confirmed: {
    cls: 'confirmed',
    icon: '✓',
    label: 'Confirmed',
    desc: 'Independently verified across multiple sources with diverse editorial leans',
    color: 'var(--confirmed)',
  },
  disputed: {
    cls: 'disputed',
    icon: '⚡',
    label: 'Disputed',
    desc: 'Sources explicitly contradict each other on this point',
    color: 'var(--disputed)',
  },
  unverified: {
    cls: 'unverified',
    icon: '◯',
    label: 'Unverifiable',
    desc: 'Single source or insufficient corroboration found',
    color: 'var(--unverified)',
  },
  opinion: {
    cls: 'opinion',
    icon: '💬',
    label: 'Opinion',
    desc: 'Framed as editorial, analysis, or interpretation — not factual reporting',
    color: 'var(--opinion)',
  },
}

function VerdictColumn({ type, claimIds, allClaims, onClaimClick }) {
  const cfg = GRADE_CONFIGS[type]
  const count = claimIds?.length || 0

  return (
    <div className={`verdict-col ${cfg.cls}`} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
        <span style={{ fontSize: 20, color: cfg.color }}>{cfg.icon}</span>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: cfg.color }}>{cfg.label}</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: cfg.color, lineHeight: 1 }}>{count}</div>
        </div>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{cfg.desc}</p>

      {count > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
          {claimIds.slice(0, 8).map(cid => (
            <button
              key={cid}
              id={`verdict-claim-${type}-${cid}`}
              onClick={() => onClaimClick?.([cid])}
              style={{
                background: 'none',
                border: `1px solid ${cfg.color}40`,
                borderRadius: 'var(--radius-sm)',
                color: cfg.color,
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                padding: '2px 6px',
                cursor: 'pointer',
                transition: 'background var(--duration-fast) var(--ease)',
              }}
              onMouseEnter={e => e.target.style.background = `${cfg.color}15`}
              onMouseLeave={e => e.target.style.background = 'none'}
            >
              {cid}
            </button>
          ))}
          {claimIds.length > 8 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              +{claimIds.length - 8} more
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default function VerdictPanel({ verdict, claims, synthesis, lang, translations, onClaimClick }) {
  if (!verdict) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 40, marginBottom: 'var(--space-3)' }}>⚖️</div>
        <p>Verdict will appear after synthesis completes</p>
      </div>
    )
  }

  const summaryText = lang === 'hi' && translations?.hi?.sections?.verdict_summary
    ? translations.hi.sections.verdict_summary
    : verdict.summary

  const execSummary = lang === 'hi' && translations?.hi?.sections?.executive_summary
    ? translations.hi.sections.executive_summary
    : synthesis?.executive_summary

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Executive summary */}
      {execSummary && (
        <div className="card" style={{
          borderLeft: '3px solid var(--accent)',
          padding: 'var(--space-5)',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-bright)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 'var(--space-3)' }}>
            EXECUTIVE SUMMARY
          </div>
          <p style={{ lineHeight: 1.7, color: 'var(--text-primary)', fontFamily: lang === 'hi' ? 'sans-serif' : 'var(--font-sans)' }}>
            {execSummary}
          </p>
        </div>
      )}

      {/* Four verdict columns */}
      <div className="verdict-grid">
        <VerdictColumn type="confirmed" claimIds={verdict.confirmed_facts} allClaims={claims} onClaimClick={onClaimClick} />
        <VerdictColumn type="disputed" claimIds={verdict.disputed_points} allClaims={claims} onClaimClick={onClaimClick} />
        <VerdictColumn type="unverified" claimIds={verdict.unverifiable_claims} allClaims={claims} onClaimClick={onClaimClick} />
        <VerdictColumn type="opinion" claimIds={verdict.opinion_claims} allClaims={claims} onClaimClick={onClaimClick} />
      </div>

      {/* Disconfirm gaps callout */}
      {verdict.disconfirm_gaps && verdict.disconfirm_gaps.length > 0 && (
        <div className="card" style={{
          borderLeft: '3px solid var(--disputed)',
          padding: 'var(--space-4) var(--space-5)',
          background: 'var(--disputed-bg)',
        }}>
          <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
            <span>⚠</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--disputed)' }}>
              Disconfirm Search Gap
            </span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            For {verdict.disconfirm_gaps.length} claim(s), a search for opposing sources was run but no
            disconfirming sources were found. <strong>Absence of opposing sources is NOT treated as confirmation.</strong>{' '}
            These claims remain unverified until cross-outlet corroboration is found.
          </p>
          <div style={{ marginTop: 'var(--space-2)', display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
            {verdict.disconfirm_gaps.map(cid => (
              <code key={cid} style={{ fontSize: 11 }}>{cid}</code>
            ))}
          </div>
        </div>
      )}

      {/* Verdict summary */}
      {summaryText && (
        <div className="card" style={{ padding: 'var(--space-5)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 'var(--space-3)' }}>
            EVIDENCE SUMMARY
          </div>
          <p style={{
            lineHeight: 1.75,
            color: 'var(--text-secondary)',
            fontFamily: lang === 'hi' ? 'sans-serif' : 'var(--font-sans)',
            whiteSpace: 'pre-wrap',
          }}>
            {summaryText}
          </p>
          <div style={{
            marginTop: 'var(--space-4)',
            padding: 'var(--space-3) var(--space-4)',
            background: 'var(--bg-elevated)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 12,
            color: 'var(--text-muted)',
            fontStyle: 'italic',
          }}>
            ℹ Veritas reports what is documented and verifiable. It does not render judgments on the legitimacy of causes, movements, or parties.
          </div>
        </div>
      )}
    </div>
  )
}
