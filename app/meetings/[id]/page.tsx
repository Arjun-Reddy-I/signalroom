'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  Check,
  Clock,
  Download,
  FileText,
  Loader2,
  Sparkles,
  Upload,
  Users,
} from 'lucide-react'
import { hasSession } from '@/lib/api/auth'
import { apiFetch } from '@/lib/api/client'

// ── Types ────────────────────────────────────────────────────────────────────

type TranscriptSegment = {
  id: string
  speaker: string
  start_time: number
  end_time: number
  text: string
  confidence: number
}

type ActionItemData = {
  id: string
  title: string
  owner_name: string | null
  due_date: string | null
  priority: string
  status: string
}

type DecisionData = {
  id: string
  title: string
  description: string | null
  category: string | null
  confidence: number
}

type MeetingDetail = {
  id: string
  title: string
  description: string | null
  status: string
  mode: string
  scheduled_start: string
  scheduled_end: string
  transcript_segments: TranscriptSegment[]
  summary: { summary_text: string; key_points_json: string; provider: string } | null
  decisions: DecisionData[]
  action_items: ActionItemData[]
  media_file: { filename: string; size_bytes: number } | null
  participants: { name: string; role: string }[]
}

type ProcessingJob = {
  id: string
  stage: string
  status: string
  error_message: string | null
  attempts: number
  updated_at: string
}

const STAGE_LABELS: Record<string, string> = {
  validate_media: 'Validating media',
  extract_audio: 'Extracting audio',
  transcribe: 'Transcribing',
  analyze: 'Analysing with AI',
  persist: 'Saving results',
  vector_embed: 'Indexing for search',
  reminders: 'Scheduling reminders',
  completed: 'Complete',
}

const STAGE_ORDER = Object.keys(STAGE_LABELS)

// ── Upload component ─────────────────────────────────────────────────────────

function UploadPanel({
  meetingId,
  onComplete,
}: {
  meetingId: string
  onComplete: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<ProcessingJob | null>(null)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  useEffect(() => {
    return () => stopPolling()
  }, [])

  async function pollJob(id: string) {
    try {
      const job = await apiFetch<ProcessingJob>(`/meetings/${meetingId}/job`)
      setJobStatus(job)
      if (job.status === 'completed' || job.status === 'failed') {
        stopPolling()
        if (job.status === 'completed') {
          setTimeout(onComplete, 1000)
        }
      }
    } catch {
      // polling errors are non-fatal
    }
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError('')
    setProgress(0)

    const formData = new FormData()
    formData.append('file', file)

    const token =
      typeof window !== 'undefined'
        ? window.localStorage.getItem('signalroom-access-token')
        : null

    return new Promise<void>((resolve) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `/api/meetings/${meetingId}/upload`)
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.setRequestHeader('Accept', 'application/json')

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 90))
      }

      xhr.onload = () => {
        if (xhr.status === 202) {
          const data = JSON.parse(xhr.responseText) as { job_id: string }
          setJobId(data.job_id)
          setProgress(100)
          setUploading(false)
          pollRef.current = setInterval(() => void pollJob(data.job_id), 2000)
        } else {
          const msg =
            (JSON.parse(xhr.responseText) as { message?: string }).message || 'Upload failed'
          setError(msg)
          setUploading(false)
        }
        resolve()
      }

      xhr.onerror = () => {
        setError('Network error during upload. Ensure the API server is running.')
        setUploading(false)
        resolve()
      }

      xhr.send(formData)
    })
  }

  const currentStageIndex = jobStatus
    ? STAGE_ORDER.indexOf(jobStatus.stage)
    : -1

  return (
    <div className="panel upload-panel">
      <div className="section-head">
        <div>
          <span className="eyebrow">Meeting recording</span>
          <h2>Upload audio</h2>
        </div>
        <Upload />
      </div>

      {!jobId && (
        <>
          <p>Upload a WAV, MP3, M4A, or WebM recording to generate a transcript and AI analysis.</p>
          <div className="upload-dropzone">
            <input
              ref={fileRef}
              type="file"
              accept="audio/*,video/webm,video/mp4"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <div className="upload-file-info">
                <FileText />
                <span>{file.name}</span>
                <small>{(file.size / 1024 / 1024).toFixed(1)} MB</small>
              </div>
            ) : (
              <button className="button-quiet" onClick={() => fileRef.current?.click()}>
                Choose file
              </button>
            )}
          </div>
          {error && <p className="form-error">{error}</p>}
          <button
            className="button-primary"
            disabled={!file || uploading}
            onClick={() => void handleUpload()}
          >
            {uploading ? (
              <>
                <Loader2 className="spin" /> Uploading… {progress}%
              </>
            ) : (
              <>
                <Upload /> Upload and process
              </>
            )}
          </button>
        </>
      )}

      {jobId && jobStatus && (
        <div className="pipeline-progress">
          <p className="eyebrow">Processing pipeline</p>
          {STAGE_ORDER.filter((s) => s !== 'completed').map((stage, i) => {
            const done = i < currentStageIndex
            const active = i === currentStageIndex
            const failed = jobStatus.status === 'failed' && active
            return (
              <div key={stage} className={`pipeline-stage ${done ? 'stage-done' : active ? (failed ? 'stage-failed' : 'stage-active') : 'stage-pending'}`}>
                <span className="stage-icon">
                  {done ? <Check /> : active && !failed ? <Loader2 className="spin" /> : active && failed ? <AlertCircle /> : <Clock />}
                </span>
                <span>{STAGE_LABELS[stage]}</span>
              </div>
            )
          })}
          {jobStatus.status === 'failed' && (
            <p className="form-error">
              Pipeline failed: {jobStatus.error_message || 'Unknown error'}
            </p>
          )}
          {jobStatus.status === 'completed' && (
            <p className="success-note">
              <Check /> Analysis complete — loading results…
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function MeetingDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const meetingId = params.id

  const [meeting, setMeeting] = useState<MeetingDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadMeeting() {
    try {
      const data = await apiFetch<MeetingDetail>(`/meetings/${meetingId}`)
      setMeeting(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load meeting'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!hasSession()) {
      router.replace('/login')
      return
    }
    void loadMeeting()
  }, [meetingId])

  if (loading) {
    return (
      <main className="auth-shell">
        <div className="auth-panel">
          <Loader2 className="spin" />
          <p>Loading meeting…</p>
        </div>
      </main>
    )
  }

  if (error || !meeting) {
    return (
      <main className="auth-shell">
        <div className="auth-panel">
          <AlertCircle />
          <h2>Meeting not found</h2>
          <p>{error || 'This meeting does not exist or you do not have access.'}</p>
          <button className="button-primary" onClick={() => router.back()}>
            Go back
          </button>
        </div>
      </main>
    )
  }

  const keyPoints: string[] = (() => {
    try {
      return JSON.parse(meeting.summary?.key_points_json || '[]') as string[]
    } catch {
      return []
    }
  })()

  const showUpload =
    !meeting.media_file && ['scheduled', 'preparing', 'failed'].includes(meeting.status)
  const isProcessing = ['uploaded', 'transcribing', 'analyzing'].includes(meeting.status)
  const isDemo =
    meeting.summary?.provider === 'demo-fallback' ||
    meeting.transcript_segments.some((s) => s.text.startsWith('[DEMO'))

  return (
    <div className="app-frame" style={{ minHeight: '100vh' }}>
      <main className="main-content" style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
        {/* Back nav */}
        <button className="text-button" onClick={() => router.back()} style={{ marginBottom: '1.5rem' }}>
          <ArrowLeft /> Back
        </button>

        {/* Header */}
        <div className="view-heading">
          <div>
            <span className="eyebrow">Meeting detail</span>
            <h1>{meeting.title}</h1>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <span className={`status meeting-status`}>{meeting.status}</span>
            <a
              href={`/api/meetings/${meetingId}/calendar.ics`}
              className="text-button"
              download
            >
              <Download /> ICS
            </a>
          </div>
        </div>

        {/* Meta row */}
        <div className="detail-grid" style={{ marginBottom: '2rem' }}>
          <div>
            <span className="eyebrow">Start</span>
            <strong>{new Date(meeting.scheduled_start).toLocaleString()}</strong>
          </div>
          <div>
            <span className="eyebrow">Mode</span>
            <strong>{meeting.mode}</strong>
          </div>
          {meeting.participants.length > 0 && (
            <div>
              <span className="eyebrow">Participants</span>
              <strong>{meeting.participants.map((p) => p.name).join(', ')}</strong>
            </div>
          )}
          {meeting.media_file && (
            <div>
              <span className="eyebrow">Recording</span>
              <strong>{meeting.media_file.filename}</strong>
            </div>
          )}
        </div>

        {isDemo && (
          <div className="panel" style={{ background: 'var(--amber-bg, #2a1f00)', borderColor: 'var(--amber, #f59e0b)', marginBottom: '1.5rem' }}>
            <p style={{ color: 'var(--amber, #f59e0b)', margin: 0 }}>
              <strong>Demo output</strong> — This transcript and analysis was generated by the fallback demo provider.
              Configure <code>STT_PROVIDER=whisper</code> and <code>LLM_PROVIDER=ollama</code> for real AI analysis.
            </p>
          </div>
        )}

        {/* Upload panel */}
        {showUpload && (
          <UploadPanel
            meetingId={meetingId}
            onComplete={() => {
              setLoading(true)
              void loadMeeting()
            }}
          />
        )}

        {/* Processing indicator */}
        {isProcessing && (
          <div className="panel" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Loader2 className="spin" />
              <span>Processing in progress — status: <strong>{meeting.status}</strong></span>
            </div>
          </div>
        )}

        {/* Summary */}
        {meeting.summary && (
          <section className="panel" style={{ marginBottom: '1.5rem' }}>
            <div className="section-head">
              <div>
                <span className="eyebrow">AI summary</span>
                <h2>Meeting summary</h2>
              </div>
              <Sparkles />
            </div>
            <p>{meeting.summary.summary_text}</p>
            {keyPoints.length > 0 && (
              <>
                <span className="eyebrow">Key points</span>
                <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
                  {keyPoints.map((pt, i) => <li key={i}>{pt}</li>)}
                </ul>
              </>
            )}
          </section>
        )}

        {/* Decisions */}
        {meeting.decisions.length > 0 && (
          <section className="panel" style={{ marginBottom: '1.5rem' }}>
            <div className="section-head">
              <div>
                <span className="eyebrow">Decisions captured</span>
                <h2>Decisions</h2>
              </div>
              <FileText />
            </div>
            {meeting.decisions.map((d) => (
              <div key={d.id} className="task-row">
                <div>
                  <strong>{d.title}</strong>
                  {d.description && <small>{d.description}</small>}
                </div>
                {d.category && <span className="priority medium">{d.category}</span>}
              </div>
            ))}
          </section>
        )}

        {/* Action items */}
        {meeting.action_items.length > 0 && (
          <section className="panel" style={{ marginBottom: '1.5rem' }}>
            <div className="section-head">
              <div>
                <span className="eyebrow">Follow-through</span>
                <h2>Action items</h2>
              </div>
              <Check />
            </div>
            {meeting.action_items.map((a) => (
              <div key={a.id} className={`task-row ${a.status === 'completed' ? 'task-done' : ''}`}>
                <div>
                  <strong>{a.title}</strong>
                  {a.owner_name && <small>Owner: {a.owner_name}</small>}
                </div>
                {a.due_date && (
                  <span>
                    <Clock style={{ width: '0.875rem' }} />{' '}
                    {new Date(a.due_date).toLocaleDateString()}
                  </span>
                )}
                <span className={`priority ${a.priority}`}>{a.priority}</span>
                <span className={`status ${a.status === 'completed' ? 'status-track' : 'status-review'}`}>
                  {a.status}
                </span>
              </div>
            ))}
          </section>
        )}

        {/* Transcript */}
        {meeting.transcript_segments.length > 0 && (
          <section className="panel" style={{ marginBottom: '1.5rem' }}>
            <div className="section-head">
              <div>
                <span className="eyebrow">Full transcript</span>
                <h2>Transcript</h2>
              </div>
              <Users />
            </div>
            <div className="transcript-list">
              {meeting.transcript_segments.map((seg) => (
                <div key={seg.id} className="transcript-segment">
                  <div className="transcript-meta">
                    <strong>{seg.speaker}</strong>
                    <small>{formatTime(seg.start_time)} – {formatTime(seg.end_time)}</small>
                  </div>
                  <p>{seg.text}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Agenda generation */}
        <AgendaSection meetingId={meetingId} />
      </main>
    </div>
  )
}

// ── Agenda section ────────────────────────────────────────────────────────────

type AgendaItem = {
  order: number
  title: string
  rationale: string
  source_type: string
  duration_minutes: number
}

function AgendaSection({ meetingId }: { meetingId: string }) {
  const [agenda, setAgenda] = useState<AgendaItem[] | null>(null)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  async function generate() {
    setGenerating(true)
    setError('')
    try {
      const res = await apiFetch<{ items: AgendaItem[]; notes: string }>(
        `/meetings/${meetingId}/agenda`,
        { method: 'POST' },
      )
      setAgenda(res.items)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Agenda generation failed')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <section className="panel" style={{ marginBottom: '1.5rem' }}>
      <div className="section-head">
        <div>
          <span className="eyebrow">Meeting preparation</span>
          <h2>Suggested agenda</h2>
        </div>
        <CalendarDays />
      </div>
      {!agenda && (
        <>
          <p>Generate a suggested agenda based on open tasks, past decisions, and meeting history.</p>
          <button
            className="button-primary"
            disabled={generating}
            onClick={() => void generate()}
          >
            {generating ? <><Loader2 className="spin" /> Generating…</> : <><Sparkles /> Generate agenda</>}
          </button>
          {error && <p className="form-error">{error}</p>}
        </>
      )}
      {agenda && (
        <div>
          {agenda.map((item) => (
            <div key={item.order} className="task-row">
              <span className="project-code">{item.order}</span>
              <div>
                <strong>{item.title}</strong>
                <small>{item.rationale.slice(0, 100)}</small>
              </div>
              <span className="eyebrow">{item.duration_minutes} min</span>
            </div>
          ))}
          <button className="text-button" style={{ marginTop: '1rem' }} onClick={() => setAgenda(null)}>
            Regenerate
          </button>
        </div>
      )}
    </section>
  )
}
