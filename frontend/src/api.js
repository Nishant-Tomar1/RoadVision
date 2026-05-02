const BASE_URL = (import.meta.env.VITE_BACKEND_URL || 'http://localhost:10000').replace(/\/$/, '')

async function request(path, init) {
  const res = await fetch(`${BASE_URL}${path}`, init)
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch (_) { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function startPrediction(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/predict', { method: 'POST', body: form })
}

export async function fetchJob(jobId, { signal } = {}) {
  return request(`/jobs/${jobId}`, { signal })
}

/**
 * Poll /jobs/:id until status is "done" or "error".
 * Snappy at the start, then backs off so long jobs don't hammer the backend.
 */
export async function pollJob(jobId, { onProgress, signal } = {}) {
  let tick = 0
  while (true) {
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
    const status = await fetchJob(jobId, { signal })
    onProgress?.(status)
    if (status.status === 'done') return status
    if (status.status === 'error') throw new Error(status.error || 'Inference failed')
    const wait = tick < 3 ? 1500 : tick < 10 ? 4000 : 8000
    await new Promise((r) => setTimeout(r, wait))
    tick++
  }
}

export async function checkHealth() {
  return request('/health')
}

export { BASE_URL }
