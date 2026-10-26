'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { loginWithEmail } from '@/lib/api/auth'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('alex@signalroom.app')
  const [password, setPassword] = useState('Password123!')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      await loginWithEmail(email, password)
      router.push('/')
      router.refresh()
    } catch {
      setError('Unable to sign in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-panel">
        <div className="auth-panel-header">
          <div className="auth-brand">
            <span className="brand-mark">S</span>
            <span>Signalroom</span>
          </div>
          <h1>Welcome back</h1>
          <p>Access your meeting intelligence workspace.</p>
        </div>
        <div className="auth-panel-body">
          <form onSubmit={handleSubmit} className="auth-form">
            <label>
              Email
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
            </label>
            <label>
              Password
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
            </label>
            {error ? <div className="auth-error">{error}</div> : null}
            <button type="submit" className="button-primary auth-button" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
          <div className="auth-links">
            <Link href="/forgot-password">Forgot password?</Link>
            <Link href="/register">Create account</Link>
          </div>
        </div>
      </div>
    </main>
  )
}
