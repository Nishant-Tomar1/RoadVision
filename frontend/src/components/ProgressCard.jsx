function formatDuration(seconds) {
  if (seconds == null || !isFinite(seconds) || seconds < 0) return '—'
  const s = Math.round(seconds)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem.toString().padStart(2, '0')}s`
}

export default function ProgressCard({ progress }) {
  const pct = Math.round((progress?.progress ?? 0) * 100)
  const frames = progress?.frames_processed ?? 0
  const total = progress?.total_frames ?? 0
  const eta = progress?.eta_seconds
  const elapsed = progress?.elapsed_seconds ?? 0

  const fps = elapsed > 0 ? (frames / elapsed) : 0
  const stage = !progress
    ? 'Uploading video…'
    : progress.frames_processed === 0
      ? 'Initializing model…'
      : pct >= 99
        ? 'Finalizing video…'
        : 'Tracking objects across frames…'

  return (
    <div className="card progress-card">
      <div className="progress-head">
        <div className="progress-spin" aria-hidden>
          <div className="spinner" />
        </div>
        <div className="progress-text">
          <div className="progress-title">{stage}</div>
          <div className="muted small">
            {total > 0 ? `${frames.toLocaleString()} of ${total.toLocaleString()} frames` : 'preparing…'}
          </div>
        </div>
        <div className="progress-pct">{pct}%</div>
      </div>

      <div className="progress-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>

      <div className="progress-stats">
        <Stat label="Elapsed" value={formatDuration(elapsed)} />
        <Stat label="ETA" value={formatDuration(eta)} />
        <Stat label="Speed" value={fps > 0 ? `${fps.toFixed(1)} fps` : '—'} />
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="progress-stat">
      <div className="progress-stat-label">{label}</div>
      <div className="progress-stat-value mono">{value}</div>
    </div>
  )
}
