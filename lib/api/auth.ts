import { apiFetch } from '@/lib/api/client'
import { isDemoModeEnabled } from '@/lib/config'

export type AuthTokenResponse = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  user?: {
    id: string
    email: string
    full_name: string
  }
}

export type AuthSession = {
  id: string
  email: string
  full_name: string
  role: string
}

export function hasSession(): boolean {
  if (typeof window === 'undefined') return false
  return Boolean(window.localStorage.getItem('signalroom-access-token'))
}

export async function loginWithEmail(email: string, password: string): Promise<AuthSession> {
  if (isDemoModeEnabled()) {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('signalroom-access-token', 'demo-access-token')
      window.localStorage.setItem('signalroom-refresh-token', 'demo-refresh-token')
      window.localStorage.setItem(
        'signalroom-user',
        JSON.stringify({ id: 'demo-user', email, full_name: 'Demo User', role: 'owner' }),
      )
    }

    return {
      id: 'demo-user',
      email,
      full_name: 'Demo User',
      role: 'owner',
    }
  }

  const payload = await apiFetch<AuthTokenResponse>('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  if (typeof window !== 'undefined') {
    window.localStorage.setItem('signalroom-access-token', payload.access_token)
    window.localStorage.setItem('signalroom-refresh-token', payload.refresh_token)
    window.localStorage.setItem(
      'signalroom-user',
      JSON.stringify({
        id: payload.user?.id ?? `user-${Date.now()}`,
        email: payload.user?.email ?? email,
        full_name: payload.user?.full_name ?? email,
        role: 'member',
      }),
    )
  }

  return {
    id: payload.user?.id ?? `user-${Date.now()}`,
    email: payload.user?.email ?? email,
    full_name: payload.user?.full_name ?? email,
    role: 'member',
  }
}

export function logoutSession(): void {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem('signalroom-access-token')
  window.localStorage.removeItem('signalroom-refresh-token')
  window.localStorage.removeItem('signalroom-user')
}
