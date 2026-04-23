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

interface ErrorMsg {
  type: 'error'
  session_id: string
  message: string
}

async function readErrorMessage(resp: Response): Promise<string> {
  try {
    const payload = await resp.json() as { detail?: string; message?: string; error?: { message?: string } }
    return payload.error?.message ?? payload.message ?? payload.detail ?? `HTTP ${resp.status}`
  } catch {
    return `HTTP ${resp.status}`
  }
}

export async function startResearch(query: string, cb: ResearchCallbacks): Promise<{ cleanup: () => void; session_id: string }> {
  let resp: Response
  const ctrl = new AbortController()
  let terminalEventReceived = false
  const timeoutId = setTimeout(() => ctrl.abort(), 30000)
  try {
    resp = await fetch('/api/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
      signal: ctrl.signal,
    })
  } catch {
    clearTimeout(timeoutId)
    cb.onError('Failed to connect to research API')
    return { cleanup: () => {}, session_id: '' }
  }
  clearTimeout(timeoutId)

  if (!resp.ok) {
    cb.onError(await readErrorMessage(resp))
    return { cleanup: () => {}, session_id: '' }
  }

  let session_id: string
  try {
    const data = await resp.json() as { session_id: string }
    session_id = data.session_id
  } catch {
    cb.onError('Invalid response from research API')
    return { cleanup: () => {}, session_id: '' }
  }
  const es = new EventSource(`/api/research/${session_id}/stream`)

  const handleProgress = (e: MessageEvent) => {
    try {
      cb.onProgress(JSON.parse(e.data) as ProgressMsg)
    } catch {
      /* ignore malformed progress message */
    }
  }
  const handleResult = (e: MessageEvent) => {
    try {
      terminalEventReceived = true
      cb.onResult(JSON.parse(e.data) as ResultMsg)
    } catch {
      cb.onError('Invalid result data')
    }
    es.close()
  }
  const handleAppError = (e: MessageEvent) => {
    try {
      terminalEventReceived = true
      const data = JSON.parse(e.data) as ErrorMsg
      cb.onError(data.message)
    } catch {
      cb.onError('Unknown server error')
    }
    es.close()
  }
  const handleGenericError = () => {
    if (terminalEventReceived || es.readyState === EventSource.CLOSED) {
      return
    }
    cb.onError('Connection lost')
    es.close()
  }

  es.addEventListener('progress', handleProgress)
  es.addEventListener('result', handleResult)
  es.addEventListener('app-error', handleAppError)
  es.onerror = handleGenericError

  return {
    cleanup: () => {
      es.removeEventListener('progress', handleProgress)
      es.removeEventListener('result', handleResult)
      es.removeEventListener('app-error', handleAppError)
      es.onerror = null
      es.close()
    },
    session_id,
  }
}

export function normalizeRole(role: string | null): string | null {
  if (!role) return null
  return role === 'evidence_deduplicator' ? 'deduplicator' : role
}
