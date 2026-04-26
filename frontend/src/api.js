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
 * Calls onProgress(jobStatus) on every tick.
 * Returns the final job status.
 */
export async function pollJob(jobId, { onProgress, intervalMs = 700, signal } = {}) {
  while (true) {
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
    const status = await fetchJob(jobId, { signal })
    onProgress?.(status)
    if (status.status === 'done') return status
    if (status.status === 'error') throw new Error(status.error || 'Inference failed')
    await new Promise((r) => setTimeout(r, intervalMs))
  }
}

export async function checkHealth() {
  return request('/health')
}

export { BASE_URL }
