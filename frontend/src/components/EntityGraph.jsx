/**
 * EntityGraph.jsx — vis-network interactive entity graph.
 * Nodes = entities (orgs/public figures). Edges = sourced claim relationships.
 */
import { useEffect, useRef } from 'react'

const NODE_COLORS = {
  organization: {
    background: 'rgba(99, 102, 241, 0.2)',
    border: '#6366f1',
    highlight: { background: 'rgba(99, 102, 241, 0.4)', border: '#818cf8' },
  },
  public_figure: {
    background: 'rgba(168, 85, 247, 0.2)',
    border: '#a855f7',
    highlight: { background: 'rgba(168, 85, 247, 0.4)', border: '#c084fc' },
  },
}

export default function EntityGraph({ entities, claims, onClaimClick }) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !entities.length) return

    // Dynamically import vis-network to avoid SSR issues
    import('vis-network/standalone').then(({ Network, DataSet }) => {
      // Build nodes
      const nodes = new DataSet(
        entities.map((e, i) => ({
          id: i,
          label: e.name,
          title: `${e.type === 'public_figure' ? '👤' : '🏛'} ${e.name}\n${e.role || ''}`,
          group: e.type,
          color: NODE_COLORS[e.type] || NODE_COLORS.organization,
          font: { color: '#f1f5f9', size: 13, face: 'Inter, sans-serif' },
          shape: e.type === 'public_figure' ? 'ellipse' : 'box',
          borderWidth: 2,
          size: 20 + Math.min(e.affiliations?.length * 4, 20),
        }))
      )

      // Build edges from shared claim references
      const edges = []
      const entityIndex = {}
      entities.forEach((e, i) => { entityIndex[e.name.toLowerCase()] = i })

      // Create edges between entities that share claim IDs
      entities.forEach((e1, i) => {
        const claimIds1 = new Set(e1.affiliations?.map(a => a.claim_id) || [])
        entities.forEach((e2, j) => {
          if (j <= i) return
          const claimIds2 = new Set(e2.affiliations?.map(a => a.claim_id) || [])
          const shared = [...claimIds1].filter(c => claimIds2.has(c))
          if (shared.length > 0) {
            edges.push({
              from: i,
              to: j,
              label: shared.slice(0, 3).join(', '),
              title: `Shared claims: ${shared.join(', ')}`,
              color: { color: 'rgba(99,102,241,0.4)', highlight: '#6366f1' },
              font: { color: '#64748b', size: 10 },
              width: 1 + Math.min(shared.length, 3),
            })
          }
        })
      })

      const edgeDataSet = new DataSet(edges)

      const options = {
        nodes: {
          margin: { top: 8, right: 12, bottom: 8, left: 12 },
        },
        edges: {
          smooth: { type: 'cubicBezier', roundness: 0.4 },
          arrows: { to: { enabled: false } },
        },
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -80,
            centralGravity: 0.01,
            springLength: 120,
            springConstant: 0.04,
          },
          stabilization: { iterations: 100 },
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          zoomView: true,
        },
        background: { color: 'transparent' },
      }

      if (networkRef.current) networkRef.current.destroy()
      const network = new Network(containerRef.current, { nodes, edges: edgeDataSet }, options)
      networkRef.current = network

      // Click node → show related claims
      network.on('click', (params) => {
        if (params.nodes.length > 0 && onClaimClick) {
          const entity = entities[params.nodes[0]]
          const relatedClaims = entity.affiliations?.map(a => a.claim_id) || []
          onClaimClick(relatedClaims)
        }
      })
    })

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [entities, claims])

  if (!entities.length) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 40, marginBottom: 'var(--space-3)' }}>🕸️</div>
        <p>Entity graph will appear after Stage 5 completes</p>
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Legend */}
      <div style={{
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-5)',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
          {entities.length} entities
        </span>
        <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
          <span style={{ fontSize: 12, color: 'var(--accent-bright)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(99,102,241,0.4)', border: '2px solid #6366f1', display: 'inline-block' }} />
            Organization
          </span>
          <span style={{ fontSize: 12, color: '#c084fc', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 12, height: 12, borderRadius: 50, background: 'rgba(168,85,247,0.4)', border: '2px solid #a855f7', display: 'inline-block' }} />
            Public Figure
          </span>
        </div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          Click a node to highlight related claims
        </span>
      </div>
      <div
        ref={containerRef}
        id="entity-graph-canvas"
        style={{
          height: 480,
          background: 'transparent',
        }}
      />
    </div>
  )
}
