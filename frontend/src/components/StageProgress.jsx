/**
 * StageProgress.jsx — Live 7-stage progress tracker driven by SSE events.
 */

const STAGES = [
  { num: 1, label: 'Decompose', icon: '🧩' },
  { num: 2, label: 'Retrieve', icon: '🌐' },
  { num: 3, label: 'Extract', icon: '🔬' },
  { num: 4, label: 'Verify', icon: '⚖️' },
  { num: 5, label: 'Graph', icon: '🕸️' },
  { num: 6, label: 'Synthesize', icon: '📝' },
  { num: 7, label: 'Translate', icon: '🌏' },
]

export default function StageProgress({ stages, activeStage, status }) {
  const getStageStatus = (num) => {
    const s = stages[num]
    if (s?.status === 'error') return 'error'
    if (s?.status === 'complete') return 'complete'
    if (num === activeStage && (status === 'streaming' || status === 'loading')) return 'active'
    return 'pending'
  }

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: 'var(--space-5) var(--space-6)',
      marginBottom: 'var(--space-6)',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 'var(--space-5)',
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
          PIPELINE STAGES
        </span>
        {status === 'complete' && (
          <span className="badge badge-confirmed animate-fade">
            ✓ Complete
          </span>
        )}
        {status === 'error' && (
          <span style={{ fontSize: 12, color: '#f43f5e', fontWeight: 600 }}>
            ⚠ Pipeline Error
          </span>
        )}
      </div>

      <div className="stage-track">
        {STAGES.map((stage, i) => {
          const stageStatus = getStageStatus(stage.num)
          const data = stages[stage.num]?.data
          return (
            <div key={stage.num} className="stage-item">
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                <div
                  className={`stage-dot ${stageStatus}`}
                  title={stage.label}
                >
                  {stageStatus === 'complete' ? '✓' :
                   stageStatus === 'error' ? '✕' :
                   stage.icon}
                </div>
                <div style={{
                  fontSize: 10,
                  fontWeight: 500,
                  color: stageStatus === 'active' ? 'var(--accent-bright)' :
                         stageStatus === 'complete' ? 'var(--confirmed)' :
                         stageStatus === 'error' ? '#f43f5e' :
                         'var(--text-muted)',
                  textAlign: 'center',
                  lineHeight: 1.2,
                  maxWidth: 60,
                  transition: 'color var(--duration) var(--ease)',
                }}>
                  {stage.label}
                </div>
                {/* Stage data badges */}
                {data && (
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    {data.page_count && `${data.page_count} pages`}
                    {data.claim_count && `${data.claim_count} claims`}
                    {data.total && !data.claim_count && `${data.total} graded`}
                    {data.entity_count && `${data.entity_count} entities`}
                    {data.sections_translated && `${data.sections_translated} sections`}
                  </div>
                )}
              </div>
              {i < STAGES.length - 1 && (
                <div
                  className={`stage-connector ${stageStatus === 'complete' ? 'complete' : ''}`}
                  style={{ marginBottom: 28 }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
