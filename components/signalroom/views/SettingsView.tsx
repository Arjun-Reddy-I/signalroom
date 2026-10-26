'use client'

import { useEffect, useState } from 'react'
import { Check, Settings2, Shield, Zap } from 'lucide-react'
import { apiFetch } from '@/lib/api/client'
import { logoutSession } from '@/lib/api/auth'
import { useRouter } from 'next/navigation'

type HealthData = {
  status: string
  environment: string
  database: string
  vector_store: string
}

type PasswordChangePayload = {
  current_password: string
  new_password: string
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        background: ok ? 'var(--success)' : 'var(--danger)',
        marginRight: '0.5rem',
      }}
    />
  )
}

export function SettingsView() {
  const router = useRouter()
  const [health, setHealth] = useState<HealthData | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)

  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwError, setPwError] = useState('')
  const [pwSuccess, setPwSuccess] = useState('')
  const [pwLoading, setPwLoading] = useState(false)

  useEffect(() => {
    void apiFetch<HealthData>('/health/ready')
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false))
  }, [])

  async function handlePasswordChange(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (newPw !== confirmPw) {
      setPwError('New passwords do not match.')
      return
    }
    if (newPw.length < 8) {
      setPwError('Password must be at least 8 characters.')
      return
    }
    setPwLoading(true)
    setPwError('')
    setPwSuccess('')
    try {
      await apiFetch<void>('/auth/password/change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: currentPw,
          new_password: newPw,
        } satisfies PasswordChangePayload),
      })
      setPwSuccess('Password changed successfully.')
      setCurrentPw('')
      setNewPw('')
      setConfirmPw('')
    } catch (err: unknown) {
      setPwError(err instanceof Error ? err.message : 'Password change failed.')
    } finally {
      setPwLoading(false)
    }
  }

  async function handleLogout() {
    await logoutSession()
    router.push('/login')
  }

  const sttProvider = typeof window !== 'undefined'
    ? (document.cookie.includes('signalroom') ? 'Connected' : 'Configured')
    : 'Unknown'

  return (
    <div className="view-stack">
      <div className="view-heading">
        <div>
          <span className="eyebrow">Workspace configuration</span>
          <h1>Settings</h1>
        </div>
        <Settings2 />
      </div>

      <div className="content-grid">
        {/* System health */}
        <section className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Infrastructure</span>
              <h2>System status</h2>
            </div>
            <Zap />
          </div>
          {healthLoading ? (
            <p className="muted-text">Checking system…</p>
          ) : !health ? (
            <p className="muted-text" style={{ color: 'var(--danger)' }}>
              API unreachable. Ensure the backend is running on port 8000.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              <div className="task-row">
                <span><StatusDot ok={health.status === 'ok'} />API</span>
                <span className="muted-text">{health.environment}</span>
                <span className={`status ${health.status === 'ok' ? 'status-track' : 'status-risk'}`}>{health.status}</span>
              </div>
              <div className="task-row">
                <span><StatusDot ok={health.database === 'connected'} />Database</span>
                <span className={`status ${health.database === 'connected' ? 'status-track' : 'status-risk'}`}>{health.database}</span>
              </div>
              <div className="task-row">
                <span><StatusDot ok={health.vector_store === 'connected'} />Vector store</span>
                <span className={`status ${health.vector_store === 'connected' ? 'status-track' : 'status-risk'}`}>{health.vector_store}</span>
              </div>
            </div>
          )}

          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
            <span className="eyebrow">AI providers</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem', fontSize: '0.875rem' }}>
              <div className="task-row">
                <span>Speech-to-Text</span>
                <code style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                  Set STT_PROVIDER in .env
                </code>
              </div>
              <div className="task-row">
                <span>Language model</span>
                <code style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                  Set LLM_PROVIDER in .env
                </code>
              </div>
              <div className="task-row">
                <span>Embeddings</span>
                <code style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                  Set EMBEDDING_PROVIDER in .env
                </code>
              </div>
              <div className="task-row">
                <span>Calendar</span>
                <span className="muted-text">ICS export available · OAuth not configured</span>
              </div>
            </div>
          </div>
        </section>

        {/* Password change */}
        <section className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Account security</span>
              <h2>Change password</h2>
            </div>
            <Shield />
          </div>
          <form onSubmit={(e) => void handlePasswordChange(e)} className="settings-form">
            <label>
              Current password
              <input
                type="password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                required
              />
            </label>
            <label>
              New password
              <input
                type="password"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                placeholder="Minimum 8 characters"
                required
              />
            </label>
            <label>
              Confirm new password
              <input
                type="password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                required
              />
            </label>
            {pwError && <p className="form-error">{pwError}</p>}
            {pwSuccess && (
              <p style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <Check style={{ width: '1rem' }} /> {pwSuccess}
              </p>
            )}
            <button type="submit" className="button-primary" disabled={pwLoading}>
              {pwLoading ? 'Updating…' : 'Update password'}
            </button>
          </form>

          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
            <span className="eyebrow" style={{ display: 'block', marginBottom: '0.75rem' }}>Session</span>
            <button className="button-quiet button-danger" onClick={() => void handleLogout()}>
              Sign out
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
