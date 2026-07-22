/**
 * App.jsx — Main Veritas application.
 * Orchestrates SearchBar → StageProgress → tabbed report view.
 */
import { useState, useRef, useCallback } from 'react'
import SearchBar from './components/SearchBar.jsx'
import StageProgress from './components/StageProgress.jsx'
import ClaimCard from './components/ClaimCard.jsx'
import EntityGraph from './components/EntityGraph.jsx'
import Timeline from './components/Timeline.jsx'
import ImageCard from './components/ImageCard.jsx'
import VerdictPanel from './components/VerdictPanel.jsx'
import { useResearch } from './hooks/useResearch.js'

const TABS = [
  { id: 'claims', label: '⚖️ Claims', desc: 'All extracted claims with grades' },
  { id: 'verdict', label: '📋 Verdict', desc: 'Evidence summary' },
  { id: 'timeline', label: '📅 Timeline', desc: 'Chronological events' },
  { id: 'graph', label: '🕸️ Entity Graph', desc: 'Organizations & figures' },
  { id: 'sources', label: '📰 Sources', desc: 'Retrieved articles' },
]

const GRADE_FILTERS = ['all', 'confirmed', 'disputed', 'unverified', 'opinion']

function Header() {
  return (
    <header style={{
      padding: 'var(--space-5) var(--space-6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      borderBottom: '1px solid var(--border)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: 'var(--bg-glass)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <span style={{ fontSize: 24 }}>⚖️</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: '-0.02em' }}>
            Veritas
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
            CLAIM VERIFICATION ENGINE
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Indian Socio-Political Research
        </span>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-ghost btn-sm"
        >
          Docs
        </a>
      </div>
    </header>
  )
}

function Hero({ onSearch, loading, lang, onLangChange }) {
  return (
    <div className="hero">
      <div className="hero-badge">
        <span>⚡</span>
        Evidence-Graded · Multi-Source · Bias-Transparent
      </div>
      <h1>Research. Verify. Report.</h1>
      <p>
        Enter any Indian socio-political topic. Veritas retrieves multi-outlet evidence,
        extracts atomic claims, cross-verifies against disconfirming sources, and grades
        each claim — with no verdict before evidence.
      </p>
      <SearchBar
        onSearch={onSearch}
        loading={loading}
        lang={lang}
        onLangChange={onLangChange}
      />
    </div>
  )
}

function SectionHeading({ label, count }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-3)',
      marginBottom: 'var(--space-5)',
    }}>
      <h2 style={{ fontSize: 18, fontWeight: 700 }}>{label}</h2>
      {count !== undefined && (
        <span className="badge badge-unverified">{count}</span>
      )}
    </div>
  )
}

function SynthesisSection({ synthesis, lang, translations }) {
  const sections = [
    { key: 'section_origin', label: '🔥 Origin' },
    { key: 'section_actors', label: '👥 Actors' },
    { key: 'section_escalation', label: '📈 Escalation' },
    { key: 'section_demands', label: '📣 Demands' },
    { key: 'section_counter_narratives', label: '🔄 Counter-Narratives' },
    { key: 'section_precedents', label: '📚 Precedents' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {sections.map(({ key, label }) => {
        const text = lang === 'hi' && translations?.hi?.sections?.[key]
          ? translations.hi.sections[key]
          : synthesis?.[key]
        if (!text) return null
        return (
          <div key={key} className="card" style={{ padding: 'var(--space-5)' }}>
            <div style={{
              fontSize: 12,
              fontWeight: 700,
              color: 'var(--accent-bright)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: 'var(--space-3)',
            }}>
              {label}
            </div>
            <p style={{
              lineHeight: 1.75,
              color: 'var(--text-secondary)',
              fontFamily: lang === 'hi' ? 'sans-serif' : 'var(--font-sans)',
            }}>
              {text}
            </p>
          </div>
        )
      })}
    </div>
  )
}

export default function App() {
  const { state, research, cancel } = useResearch()
  const [activeTab, setActiveTab] = useState('claims')
  const [gradeFilter, setGradeFilter] = useState('all')
  const [lang, setLang] = useState('en')
  const [highlightedClaims, setHighlightedClaims] = useState(null)
  const claimsRef = useRef(null)

  const isActive = state.status === 'loading' || state.status === 'streaming'
  const hasData = state.status === 'complete' || state.claims.length > 0

  const handleSearch = useCallback((topic, language) => {
    setActiveTab('claims')
    setGradeFilter('all')
    setHighlightedClaims(null)
    research(topic, language)
  }, [research])

  const handleClaimClick = useCallback((claimIds) => {
    setHighlightedClaims(new Set(claimIds))
    setActiveTab('claims')
    // Scroll to first matched claim
    setTimeout(() => {
      const el = document.getElementById(`claim-${claimIds[0]}`)
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)
  }, [])

  const filteredClaims = state.claims.filter(c =>
    gradeFilter === 'all' || c.grade === gradeFilter
  )

  const gradeCounts = state.claims.reduce((acc, c) => {
    acc[c.grade] = (acc[c.grade] || 0) + 1
    return acc
  }, {})

  return (
    <div className="page">
      <Header />

      {/* Hero / Search */}
      <div className={hasData ? '' : ''}>
        {!hasData ? (
          <div className="container">
            <Hero
              onSearch={handleSearch}
              loading={isActive}
              lang={lang}
              onLangChange={setLang}
            />
          </div>
        ) : (
          <div style={{
            padding: 'var(--space-6) var(--space-6) 0',
            maxWidth: 1200,
            margin: '0 auto',
          }}>
            <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'center', marginBottom: 'var(--space-5)' }}>
              <div style={{ flex: 1 }}>
                <SearchBar
                  onSearch={handleSearch}
                  loading={isActive}
                  lang={lang}
                  onLangChange={setLang}
                />
              </div>
              {isActive && (
                <button className="btn btn-ghost btn-sm" onClick={cancel}>
                  ✕ Cancel
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Main content */}
      {(isActive || hasData) && (
        <div className="container" style={{ paddingBottom: 'var(--space-16)', flex: 1 }}>
          {/* Topic heading */}
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
              marginBottom: 'var(--space-2)',
            }}>
              <h2 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.02em' }}>
                {state.topic}
              </h2>
              {state.status === 'complete' && (
                <span className="badge badge-confirmed animate-fade">
                  ✓ Research Complete
                </span>
              )}
              {isActive && (
                <span className="badge" style={{
                  background: 'var(--accent-dim)',
                  color: 'var(--accent-bright)',
                  border: '1px solid rgba(99,102,241,0.3)',
                  animation: 'pulse-ring 1.5s infinite',
                }}>
                  ◉ Live
                </span>
              )}
            </div>
            {/* Sub-questions */}
            {state.subQuestions.length > 0 && (
              <details style={{ marginTop: 'var(--space-2)' }}>
                <summary style={{
                  fontSize: 12,
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}>
                  {state.subQuestions.length} sub-questions generated
                </summary>
                <div style={{
                  marginTop: 'var(--space-3)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-2)',
                }}>
                  {state.subQuestions.map((q, i) => (
                    <div key={i} style={{
                      fontSize: 12,
                      color: 'var(--text-secondary)',
                      paddingLeft: 'var(--space-4)',
                      borderLeft: '2px solid var(--accent-dim)',
                    }}>
                      {q}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>

          {/* Stage Progress */}
          <StageProgress
            stages={state.stages}
            activeStage={state.activeStage}
            status={state.status}
          />

          {/* Error display */}
          {Object.keys(state.errors).length > 0 && (
            <div className="card" style={{
              borderLeft: '3px solid #f43f5e',
              background: 'rgba(244,63,94,0.08)',
              padding: 'var(--space-4)',
              marginBottom: 'var(--space-5)',
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#f43f5e', marginBottom: 'var(--space-2)' }}>
                ⚠ Pipeline Errors (partial results shown)
              </div>
              {Object.entries(state.errors).map(([k, v]) => (
                <div key={k} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  <code>{k}</code>: {v}
                </div>
              ))}
            </div>
          )}

          {/* Tabs */}
          <div className="tabs" style={{ marginBottom: 'var(--space-6)' }}>
            {TABS.map(tab => {
              const count = tab.id === 'claims' ? state.claims.length
                : tab.id === 'timeline' ? state.timeline.length
                : tab.id === 'graph' ? state.entities.length
                : tab.id === 'sources' ? state.images.length
                : null
              return (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  className={`tab ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                  {count !== null && count > 0 && (
                    <span style={{
                      marginLeft: 4,
                      background: activeTab === tab.id ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                      color: activeTab === tab.id ? 'var(--accent-bright)' : 'var(--text-muted)',
                      borderRadius: 'var(--radius-full)',
                      fontSize: 11,
                      padding: '1px 6px',
                    }}>
                      {count}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* ── Claims Tab ─────────────────────────────────────── */}
          {activeTab === 'claims' && (
            <div ref={claimsRef}>
              {/* Grade filter bar */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                marginBottom: 'var(--space-5)',
                flexWrap: 'wrap',
              }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                  FILTER:
                </span>
                {GRADE_FILTERS.map(g => {
                  const count = g === 'all' ? state.claims.length : (gradeCounts[g] || 0)
                  return (
                    <button
                      key={g}
                      id={`filter-${g}`}
                      onClick={() => setGradeFilter(g)}
                      className={`btn btn-sm ${gradeFilter === g ? 'btn-primary' : 'btn-ghost'}`}
                      style={gradeFilter !== g ? {
                        color: g === 'confirmed' ? 'var(--confirmed)' :
                               g === 'disputed' ? 'var(--disputed)' :
                               g === 'unverified' ? 'var(--unverified)' :
                               g === 'opinion' ? 'var(--opinion)' :
                               'var(--text-secondary)',
                      } : {}}
                    >
                      {g.charAt(0).toUpperCase() + g.slice(1)}
                      <span style={{ marginLeft: 2, opacity: 0.7 }}>({count})</span>
                    </button>
                  )
                })}
              </div>

              <SectionHeading
                label="Extracted Claims"
                count={filteredClaims.length}
              />

              {filteredClaims.length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 'var(--space-12)' }}>
                  {isActive ? (
                    <>
                      <div className="spinner" style={{ margin: '0 auto var(--space-4)' }} />
                      <p>Extracting claims…</p>
                    </>
                  ) : (
                    <p>No claims match this filter.</p>
                  )}
                </div>
              )}

              {filteredClaims.map((claim, i) => (
                <div
                  key={claim.id}
                  style={{
                    animationDelay: `${i * 40}ms`,
                    outline: highlightedClaims?.has(claim.id)
                      ? '2px solid var(--accent)'
                      : 'none',
                    borderRadius: 'var(--radius-lg)',
                    transition: 'outline var(--duration) var(--ease)',
                  }}
                >
                  <ClaimCard
                    claim={claim}
                    lang={lang}
                    translations={state.translations}
                  />
                </div>
              ))}
            </div>
          )}

          {/* ── Verdict Tab ─────────────────────────────────────── */}
          {activeTab === 'verdict' && (
            <div>
              <SectionHeading label="Evidence Summary" />
              <VerdictPanel
                verdict={state.verdict}
                claims={state.claims}
                synthesis={state.synthesis}
                lang={lang}
                translations={state.translations}
                onClaimClick={handleClaimClick}
              />
              {state.synthesis && (
                <div style={{ marginTop: 'var(--space-6)' }}>
                  <SectionHeading label="Research Sections" />
                  <SynthesisSection
                    synthesis={state.synthesis}
                    lang={lang}
                    translations={state.translations}
                  />
                </div>
              )}
            </div>
          )}

          {/* ── Timeline Tab ─────────────────────────────────────── */}
          {activeTab === 'timeline' && (
            <div>
              <SectionHeading label="Timeline of Events" count={state.timeline.length} />
              <Timeline
                events={state.timeline}
                claims={state.claims}
                onClaimClick={handleClaimClick}
              />
            </div>
          )}

          {/* ── Graph Tab ─────────────────────────────────────── */}
          {activeTab === 'graph' && (
            <div>
              <SectionHeading label="Entity Relationship Graph" count={state.entities.length} />
              <EntityGraph
                entities={state.entities}
                claims={state.claims}
                onClaimClick={handleClaimClick}
              />
            </div>
          )}

          {/* ── Sources Tab ─────────────────────────────────────── */}
          {activeTab === 'sources' && (
            <div>
              <SectionHeading label="Retrieved Sources" count={state.images.length} />
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 'var(--space-4)',
              }}>
                {state.images.map((img, i) => (
                  <ImageCard key={i} image={img} />
                ))}
              </div>
              {state.images.length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 'var(--space-12)' }}>
                  {isActive ? (
                    <>
                      <div className="spinner" style={{ margin: '0 auto var(--space-4)' }} />
                      <p>Retrieving sources…</p>
                    </>
                  ) : (
                    <p>No sources available.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: 'var(--space-6)',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: 12,
        lineHeight: 1.6,
      }}>
        <p>
          <strong style={{ color: 'var(--text-secondary)' }}>Veritas</strong> — Evidence-graded research.
          Grades reflect source availability and corroboration, not editorial judgment.
          No verdict is rendered on the legitimacy of any cause or movement.
        </p>
        <p style={{ marginTop: 'var(--space-2)', opacity: 0.6 }}>
          Powered by Groq (Llama 3.3 70B) · Tavily Search · LangGraph
        </p>
      </footer>
    </div>
  )
}
