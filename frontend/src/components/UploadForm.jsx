import { useRef, useState } from 'react'

const ALLOWED_RE = /\.(mp4|mov|avi|webm|mkv)$/i

export default function UploadForm({ onSubmit, disabled, hasResult, onReset }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const pick = () => inputRef.current?.click()

  const handleFile = (f) => {
    setError('')
    if (!f) { setFile(null); return }
    if (!ALLOWED_RE.test(f.name)) {
      setError('Please choose a video file (mp4, mov, avi, webm, mkv).')
      setFile(null)
      return
    }
    setFile(f)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!file) { setError('Pick a video first.'); return }
    onSubmit(file)
  }

  const handleClear = () => {
    setFile(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
    onReset?.()
  }

  return (
    <form className="card upload" onSubmit={handleSubmit}>
      <div className="card-head">
        <h3 className="card-title">Upload a road video</h3>
        <span className="muted small">Max 100 MB · runs on CPU</span>
      </div>

      <label
        className={`dropzone ${file ? 'has-file' : ''} ${dragOver ? 'is-drag' : ''} ${disabled ? 'is-disabled' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          if (disabled) return
          handleFile(e.dataTransfer.files?.[0])
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          onChange={(e) => handleFile(e.target.files?.[0])}
          disabled={disabled}
          hidden
        />
        {file ? (
          <div className="dropzone-file">
            <div className="file-icon" aria-hidden>
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="6" width="13" height="12" rx="2" />
                <path d="m16 10 5-3v10l-5-3z" />
              </svg>
            </div>
            <div className="file-meta">
              <div className="file-name">{file.name}</div>
              <div className="muted small">{(file.size / (1024 * 1024)).toFixed(2)} MB · {file.type || 'video'}</div>
            </div>
            <button type="button" className="icon-btn" onClick={(e) => { e.preventDefault(); handleClear() }} aria-label="Remove file">×</button>
          </div>
        ) : (
          <div className="dropzone-empty">
            <div className="dz-glyph" aria-hidden>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 16V4" />
                <path d="m6 10 6-6 6 6" />
                <path d="M4 20h16" />
              </svg>
            </div>
            <div className="dz-title">Drag &amp; drop your video</div>
            <div className="muted small">or <button type="button" className="link" onClick={pick}>browse files</button> · mp4, mov, avi, webm, mkv</div>
          </div>
        )}
      </label>

      {error && <p className="inline-error">{error}</p>}

      <div className="actions">
        {(file || hasResult) && !disabled && (
          <button type="button" className="btn ghost" onClick={handleClear}>
            Reset
          </button>
        )}
        <button type="submit" className="btn primary" disabled={disabled || !file}>
          {disabled ? (
            <>
              <span className="btn-spinner" aria-hidden />
              Processing…
            </>
          ) : (
            <>
              Run detection
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </>
          )}
        </button>
      </div>
    </form>
  )
}
