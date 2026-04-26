export default function StatusBar({ health, baseUrl }) {
  const state = !health ? 'loading' : health.model_loaded ? 'ok' : 'down'
  const label = state === 'loading'
    ? 'Connecting…'
    : state === 'ok' ? 'Model online' : 'Model offline'

  const host = (() => {
    try { return new URL(baseUrl).host } catch { return baseUrl }
  })()

  return (
    <div className={`status status-${state}`} title={baseUrl}>
      <span className="status-dot" />
      <span className="status-label">{label}</span>
      <span className="status-sep">·</span>
      <span className="status-host">{host}</span>
    </div>
  )
}
