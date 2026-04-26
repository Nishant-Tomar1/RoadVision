import { useEffect, useRef, useState } from 'react'
import UploadForm from './components/UploadForm.jsx'
import ResultDisplay from './components/ResultDisplay.jsx'
import ProgressCard from './components/ProgressCard.jsx'
import StatusBar from './components/StatusBar.jsx'
import { BASE_URL, checkHealth, pollJob, startPrediction } from './api.js'

export default function App() {
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [health, setHealth] = useState(null)
  const abortRef = useRef(null)

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'down', model_loaded: false, classes: [] }))
  }, [])

  const handleSubmit = async (file) => {
    setBusy(true)
    setError('')
    setResult(null)
    setProgress(null)

    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const accepted = await startPrediction(file)
      setProgress({
        status: 'processing',
        progress: 0,
        frames_processed: 0,
        total_frames: accepted.total_frames,
        elapsed_seconds: 0,
        eta_seconds: null,
      })
      const final = await pollJob(accepted.job_id, {
        onProgress: setProgress,
        intervalMs: 700,
        signal: ctrl.signal,
      })
      setResult({ ...final.result, job_id: final.job_id })
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message || 'Something went wrong while processing the video.')
      }
    } finally {
      setBusy(false)
      setProgress(null)
      abortRef.current = null
    }
  }

  const handleReset = () => {
    abortRef.current?.abort()
    setResult(null)
    setError('')
    setProgress(null)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 18 9 6l3 6 3-3 6 9z" />
              </svg>
            </div>
            <div className="brand-text">
              <div className="brand-name">RoadVision</div>
              <div className="brand-tag">AI Road Damage Detection</div>
            </div>
          </div>
          <StatusBar health={health} baseUrl={BASE_URL} />
        </div>
      </header>

      <section className="hero">
        <div className="container">
          <span className="eyebrow">YOLOv8 · ByteTrack · FastAPI</span>
          <h1>Detect and count road damage<br />from any dashcam video.</h1>
          <p className="lede">
            Upload a road clip and our model tracks every pothole, crack, and manhole
            across frames — returning a fully annotated video and per-class unique counts
            you can act on.
          </p>
        </div>
      </section>

      <main className="container main">
        <div className="layout">
          <div className="col-main">
            <UploadForm onSubmit={handleSubmit} disabled={busy} hasResult={!!result} onReset={handleReset} />

            {busy && <ProgressCard progress={progress} />}

            {error && (
              <div className="card error-card" role="alert">
                <div className="error-icon" aria-hidden>!</div>
                <div>
                  <div className="error-title">Something went wrong</div>
                  <div className="error-sub">{error}</div>
                </div>
              </div>
            )}

            <ResultDisplay result={result} />
          </div>

          <aside className="col-side">
            <div className="card legend">
              <h3 className="card-title">Detected classes</h3>
              <p className="muted small">The model is trained on three categories of road defects.</p>
              <ul className="legend-list">
                <li>
                  <span className="dot dot-pothole" />
                  <div>
                    <div className="legend-name">Pothole</div>
                    <div className="muted small">Surface depressions and broken asphalt.</div>
                  </div>
                </li>
                <li>
                  <span className="dot dot-crack" />
                  <div>
                    <div className="legend-name">Crack</div>
                    <div className="muted small">Linear surface fractures and seams.</div>
                  </div>
                </li>
                <li>
                  <span className="dot dot-manhole" />
                  <div>
                    <div className="legend-name">Manhole</div>
                    <div className="muted small">Utility access covers (filtered as non-damage).</div>
                  </div>
                </li>
              </ul>
            </div>

            <div className="card model-info">
              <h3 className="card-title">How it works</h3>
              <ol className="steps">
                <li><span>1</span>Upload a road video (mp4, mov, avi, webm, mkv).</li>
                <li><span>2</span>YOLOv8 runs detection on each frame.</li>
                <li><span>3</span>ByteTrack assigns persistent IDs across frames.</li>
                <li><span>4</span>You get an annotated video and unique counts.</li>
              </ol>
            </div>
          </aside>
        </div>
      </main>

      <footer className="footer">
        <div className="container footer-inner">
          <span className="muted small">RoadVision · BTP Project</span>
          <span className="muted small">Built with FastAPI · React · YOLOv8 · ByteTrack</span>
        </div>
      </footer>
    </div>
  )
}
