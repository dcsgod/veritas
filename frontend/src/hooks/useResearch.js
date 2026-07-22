/**
 * useResearch.js — SSE stream consumer for the Veritas research pipeline.
 * Accumulates partial state as each stage completes.
 */
import { useState, useRef, useCallback } from 'react'

const STAGE_NAMES = {
  1: 'Topic Decomposition',
  2: 'Multi-Source Retrieval',
  3: 'Claim Extraction',
  4: 'Cross-Verification & Grading',
  5: 'Entity & Timeline Graph',
  6: 'Report Synthesis',
  7: 'Hindi Translation',
}

const initialState = {
  status: 'idle',        // idle | loading | streaming | complete | error
  topic: '',
  stages: {},            // stage number → { label, status, data }
  subQuestions: [],
  claims: [],
  entities: [],
  timeline: [],
  images: [],
  verdict: null,
  synthesis: null,
  translations: {},
  errors: {},
  activeStage: 0,
}

export function useResearch() {
  const [state, setState] = useState(initialState)
  const esRef = useRef(null)

  const cancel = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    setState(s => ({ ...s, status: 'idle' }))
  }, [])

  const research = useCallback(async (topic, language = 'en') => {
    // Close any existing stream
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    setState({
      ...initialState,
      status: 'loading',
      topic,
    })

    try {
      // POST to kick off the pipeline — backend returns SSE stream
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, language }),
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(err.detail || 'Research request failed')
      }

      setState(s => ({ ...s, status: 'streaming' }))

      // Read the SSE stream manually (fetch ReadableStream)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const processChunk = (chunk) => {
        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const event = JSON.parse(raw)
            handleEvent(event)
          } catch (e) {
            console.warn('SSE parse error:', e, raw)
          }
        }
      }

      const handleEvent = (event) => {
        const { type } = event

        if (type === 'start') {
          setState(s => ({ ...s, topic: event.topic }))

        } else if (type === 'stage_complete') {
          setState(s => ({
            ...s,
            activeStage: event.stage,
            stages: {
              ...s.stages,
              [event.stage]: {
                label: event.label || STAGE_NAMES[event.stage],
                status: event.status,
                data: event.data,
                error: event.error,
              },
            },
            subQuestions: event.data?.sub_questions || s.subQuestions,
          }))

        } else if (type === 'partial_claims') {
          setState(s => ({
            ...s,
            claims: event.claims || s.claims,
          }))

        } else if (type === 'partial_claims_graded') {
          setState(s => ({
            ...s,
            claims: event.claims || s.claims,
          }))

        } else if (type === 'partial_graph') {
          setState(s => ({
            ...s,
            entities: event.entities || s.entities,
            timeline: event.timeline || s.timeline,
            images: event.images || s.images,
          }))

        } else if (type === 'report_complete') {
          const { report, synthesis, errors } = event
          setState(s => ({
            ...s,
            status: 'complete',
            claims: report?.claims || s.claims,
            entities: report?.entities || s.entities,
            timeline: report?.timeline || s.timeline,
            images: report?.images || s.images,
            verdict: report?.verdict || s.verdict,
            translations: report?.translations || {},
            subQuestions: report?.sub_questions || s.subQuestions,
            synthesis: synthesis || null,
            errors: errors || {},
          }))

        } else if (type === 'error') {
          setState(s => ({
            ...s,
            status: 'error',
            errors: { ...s.errors, pipeline: event.message },
          }))

        } else if (type === 'done') {
          setState(s => ({
            ...s,
            status: s.status === 'streaming' ? 'complete' : s.status,
          }))
        }
      }

      // Read loop
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        processChunk(decoder.decode(value, { stream: true }))
      }

    } catch (err) {
      console.error('Research error:', err)
      setState(s => ({
        ...s,
        status: 'error',
        errors: { ...s.errors, fetch: err.message },
      }))
    }
  }, [])

  return { state, research, cancel }
}
