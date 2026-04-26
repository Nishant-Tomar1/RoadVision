export default function ResultDisplay({ result }) {
  if (!result) return null
  const { video_url, download_url, counts, total_unique_objects, frames_processed, inference_seconds, job_id } = result

  const fps = frames_processed && inference_seconds
    ? (frames_processed / inference_seconds).toFixed(1)
    : '—'

  return (
    <section className="card result">
      <div className="card-head">
        <div>
          <h3 className="card-title">Detection complete</h3>
          <div className="muted small mono">job · {job_id}</div>
        </div>
        <a className="btn ghost small" href={download_url}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 4v12" /><path d="m6 12 6 6 6-6" /><path d="M4 20h16" />
          </svg>
          Download video
        </a>
      </div>

      <div className="video-wrap">
        <video controls src={video_url} className="video" />
      </div>

      <div className="metrics">
        <Metric label="Unique objects" value={total_unique_objects} accent="violet" />
        <Metric label="Frames processed" value={frames_processed} />
        <Metric label="Inference time" value={`${inference_seconds}s`} />
        <Metric label="Throughput" value={`${fps} fps`} />
      </div>

      <div className="counts-block">
        <h4 className="block-title">Per-class unique counts</h4>
        <div className="counts-grid">
          {counts.map((c) => (
            <div key={c.class_name} className={`count-card count-${c.class_name}`}>
              <div className="count-head">
                <span className={`pill pill-${c.class_name}`}>{c.class_name}</span>
              </div>
              <div className="count-value">{c.count}</div>
              <div className="count-bar" aria-hidden>
                <div
                  className="count-bar-fill"
                  style={{ width: `${barWidth(c.count, counts)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value, accent }) {
  return (
    <div className={`metric ${accent ? `metric-${accent}` : ''}`}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  )
}

function barWidth(value, all) {
  const max = Math.max(1, ...all.map((c) => c.count))
  return Math.max(4, (value / max) * 100)
}
