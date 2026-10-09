'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

import { apiFetch } from '@/lib/api/client'

export default function RegisterPage() {
  const router = useRouter()
  const [fullName, setFullName] = useState('Alex Morgan')
  const [email, setEmail] = useState('alex@signalroom.app')
  const [password, setPassword] = useState('Password123!')
  const [organizationName, setOrganizationName] = useState('SignalRoom Studio')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const payload = await apiFetch<{ access_token: string; refresh_token: string; user?: { id: string; email: string; full_name: string } }>('/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: fullName,
          email,
          password,
          organization_name: organizationName,
        }),
      })

      if (typeof window !== 'undefined') {
        window.localStorage.setItem('signalroom-access-token', payload.access_token)
        window.localStorage.setItem('signalroom-refresh-token', payload.refresh_token)
        window.localStorage.setItem('signalroom-user', JSON.stringify(payload.user ?? { email, full_name: fullName }))
      }

      router.push('/')
      router.refresh()
    } catch {
      setError('Unable to create the workspace. Please check the details and try again.')
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
        <h1>Create your workspace</h1>
        <p>Bring meetings, decisions, and follow-through into one system.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Full name
            <input type="text" value={fullName} onChange={(event) => setFullName(event.target.value)} />
          </label>
          <label>
            Workspace name
            <input type="text" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} />
          </label>
          <label>
            Work email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error ? <div className="auth-error">{error}</div> : null}
          <button type="submit" className="button-primary auth-button" disabled={loading}>
            {loading ? 'Creating workspace...' : 'Create account'}
          </button>
        </form>
        <div className="auth-links">
          <Link href="/login">Already have an account?</Link>
        </div>
      </div>
    </main>
  )
}
