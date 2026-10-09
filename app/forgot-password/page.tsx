'use client'

import Link from 'next/link'
import { useState } from 'react'

import { apiFetch } from '@/lib/api/client'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('alex@signalroom.app')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    setError('')

    try {
      await apiFetch<{ message: string }>('/auth/password/forgot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })

      setMessage('If the account exists, a secure reset token has been dispatched.')
    } catch {
      setError('We could not process that request right now. Please try again.')
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
        <h1>Reset password</h1>
        <p>We’ll send a secure reset link to your email.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input type="email" placeholder="you@company.com" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          {message ? <div className="auth-success">{message}</div> : null}
          {error ? <div className="auth-error">{error}</div> : null}
          <button type="submit" className="button-primary auth-button" disabled={loading}>
            {loading ? 'Sending reset link...' : 'Send reset link'}
          </button>
        </form>
        <div className="auth-links">
          <Link href="/login">Back to sign in</Link>
        </div>
      </div>
    </main>
  )
}
