export interface ProgressMsg {
  type: 'progress'
  session_id: string
  phase: string
  role: string | null
  step_index: number
  total_steps: number
  substep_label: string
  substep_index: number
  substep_total: number
  detail: string
  elapsed_ms: number | null
}

export interface BackendSource {
  url: string
  title: string
}

export interface BackendClaim {
  text: string
  verdict: string
  confidence: number
  sources: string[]
  evidence: string | null
}

export interface ResultMsg {
  type: 'result'
  session_id: string
  report: string
  sources: BackendSource[]
  claims: BackendClaim[]
  error: string | null
}

export interface ResearchCallbacks {
  onProgress(e: ProgressMsg): void
  onResult(e: ResultMsg): void
  onError(msg: string): void
}

export async function startResearch(query: string, cb: ResearchCallbacks): Promise<() => void> {
  let resp: Response
  try {
    resp = await fetch('/api/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
  } catch {
    cb.onError('Failed to connect to research API')
    return () => {}
  }

  if (!resp.ok) {
    cb.onError(`HTTP ${resp.status}`)
    return () => {}
  }

  const { session_id } = await resp.json() as { session_id: string }
  const es = new EventSource(`/api/research/${session_id}/stream`)

  es.addEventListener('progress', (e) => {
    cb.onProgress(JSON.parse((e as MessageEvent).data) as ProgressMsg)
  })
  es.addEventListener('result', (e) => {
    cb.onResult(JSON.parse((e as MessageEvent).data) as ResultMsg)
    es.close()
  })
  es.addEventListener('error', (e) => {
    const data = JSON.parse((e as MessageEvent).data) as { message: string }
    cb.onError(data.message)
    es.close()
  })
  es.onerror = () => {
    cb.onError('Connection lost')
    es.close()
  }

  return () => es.close()
}

export function normalizeRole(role: string | null): string | null {
  if (!role) return null
  return role === 'evidence_deduplicator' ? 'deduplicator' : role
}
