/**
 * ImageCard.jsx — Source image with attribution from cited pages.
 */
export default function ImageCard({ image }) {
  return (
    <div
      id={`image-${encodeURIComponent(image.url).slice(0, 20)}`}
      className="card animate-in"
      style={{ padding: 0, overflow: 'hidden' }}
    >
      {/* Article link preview card */}
      <a
        href={image.source_url}
        target="_blank"
        rel="noopener noreferrer"
        style={{ display: 'block', textDecoration: 'none' }}
      >
        <div style={{
          background: 'linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-hover) 100%)',
          padding: 'var(--space-6)',
          minHeight: 120,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Decorative background pattern */}
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `repeating-linear-gradient(
              -45deg,
              rgba(99, 102, 241, 0.03) 0px,
              rgba(99, 102, 241, 0.03) 1px,
              transparent 1px,
              transparent 8px
            )`,
          }} />
          <span style={{ fontSize: 32, position: 'relative' }}>📰</span>
        </div>
      </a>

      {/* Caption + attribution */}
      <div style={{ padding: 'var(--space-4)' }}>
        <p style={{
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--text-primary)',
          lineHeight: 1.5,
          marginBottom: 'var(--space-2)',
        }}>
          {image.caption}
        </p>
        <p style={{
          fontSize: 11,
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}>
          <span>📎</span>
          <a
            href={image.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--accent-bright)', fontSize: 11 }}
          >
            {image.attribution}
          </a>
        </p>
      </div>
    </div>
  )
}
