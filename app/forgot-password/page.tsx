'use client'

import { useState } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api/client'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await apiFetch('/auth/password/forgot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      setSent(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark">S</span>
          <span>Signalroom</span>
        </div>
        <h1>Forgot password</h1>
        {sent ? (
          <>
            <p>
              If that account exists, a reset token has been sent. Check your inbox (or the
              server console in development mode).
            </p>
            <Link href="/reset-password" className="button-primary auth-button" style={{ display: 'block', textAlign: 'center' }}>
              Enter reset token
            </Link>
          </>
        ) : (
          <form onSubmit={(e) => void handleSubmit(e)} className="auth-form">
            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            {error && <div className="auth-error">{error}</div>}
            <button type="submit" className="button-primary auth-button" disabled={loading}>
              {loading ? 'Sending…' : 'Send reset token'}
            </button>
          </form>
        )}
        <div className="auth-links">
          <Link href="/login">Back to sign in</Link>
        </div>
      </div>
    </main>
  )
}
