/**
 * SearchBar.jsx — Topic input with example queries and language toggle.
 */
import { useState } from 'react'

const EXAMPLES = [
  'CJP protest in Delhi 2026',
  'NEET paper leak controversy',
  'Manipur ethnic violence',
  'Farmers protest MSP demand',
  'Waqf Amendment Bill protests',
]

export default function SearchBar({ onSearch, loading, lang, onLangChange }) {
  const [topic, setTopic] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (topic.trim() && !loading) {
      onSearch(topic.trim(), lang)
    }
  }

  const handleExample = (ex) => {
    setTopic(ex)
    if (!loading) onSearch(ex, lang)
  }

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <form onSubmit={handleSubmit} style={{ position: 'relative' }}>
        <div style={{
          display: 'flex',
          gap: 'var(--space-3)',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-2)',
          boxShadow: 'var(--shadow-md), 0 0 60px rgba(99, 102, 241, 0.1)',
          transition: 'box-shadow var(--duration) var(--ease)',
        }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <span style={{
              position: 'absolute',
              left: 'var(--space-4)',
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: 18,
              lineHeight: 1,
            }}>🔍</span>
            <input
              id="research-topic-input"
              className="input"
              style={{
                background: 'transparent',
                border: 'none',
                paddingLeft: 'calc(var(--space-4) + 28px)',
                fontSize: 16,
                boxShadow: 'none',
              }}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter a topic to research (e.g. CJP protest in Delhi)…"
              disabled={loading}
              autoFocus
            />
          </div>

          <button
            id="lang-toggle-btn"
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onLangChange(lang === 'en' ? 'hi' : 'en')}
            style={{ flexShrink: 0 }}
          >
            {lang === 'en' ? '🇮🇳 हिं' : '🇬🇧 EN'}
          </button>

          <button
            id="research-submit-btn"
            type="submit"
            className="btn btn-primary"
            disabled={loading || !topic.trim()}
            style={{ flexShrink: 0, borderRadius: 'var(--radius-lg)' }}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16 }} />
                Researching…
              </>
            ) : (
              <>⚖️ Verify</>
            )}
          </button>
        </div>
      </form>

      {/* Example queries */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        marginTop: 'var(--space-4)',
        flexWrap: 'wrap',
        justifyContent: 'center',
      }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>Examples:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            id={`example-${ex.replace(/\s+/g, '-').toLowerCase()}`}
            type="button"
            onClick={() => handleExample(ex)}
            disabled={loading}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-full)',
              color: 'var(--text-secondary)',
              fontSize: 12,
              padding: '4px 12px',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all var(--duration-fast) var(--ease)',
              fontFamily: 'var(--font-sans)',
            }}
            onMouseEnter={(e) => {
              e.target.style.borderColor = 'var(--accent)'
              e.target.style.color = 'var(--accent-bright)'
            }}
            onMouseLeave={(e) => {
              e.target.style.borderColor = 'var(--border)'
              e.target.style.color = 'var(--text-secondary)'
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}
