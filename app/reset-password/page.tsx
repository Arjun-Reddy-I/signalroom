'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { apiFetch } from '@/lib/api/client'

function ResetPasswordForm() {
  const router = useRouter()
  const params = useSearchParams()
  const [token, setToken] = useState(params.get('token') ?? '')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await apiFetch('/auth/password/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      setDone(true)
      setTimeout(() => router.push('/login'), 2000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Reset failed. The token may be invalid or expired.')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <main className="auth-shell">
        <div className="auth-panel">
          <div className="auth-brand">
            <span className="brand-mark">S</span>
            <span>Signalroom</span>
          </div>
          <h1>Password reset</h1>
          <p>Your password has been updated. Redirecting to sign in…</p>
        </div>
      </main>
    )
  }

  return (
    <main className="auth-shell">
      <div className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark">S</span>
          <span>Signalroom</span>
        </div>
        <h1>Reset password</h1>
        <p>Enter the token from your email and choose a new password.</p>
        <form onSubmit={(e) => void handleSubmit(e)} className="auth-form">
          <label>
            Reset token
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste token from email"
              required
            />
          </label>
          <label>
            New password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              required
            />
          </label>
          <label>
            Confirm password
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repeat new password"
              required
            />
          </label>
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" className="button-primary auth-button" disabled={loading}>
            {loading ? 'Resetting…' : 'Reset password'}
          </button>
        </form>
        <div className="auth-links">
          <Link href="/login">Back to sign in</Link>
        </div>
      </div>
    </main>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  )
}
