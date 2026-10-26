import { API_BASE_URL } from '@/lib/config'

export type ApiErrorShape = {
  message: string
  details?: Record<string, unknown>
}

export class SignalRoomApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'SignalRoomApiError'
  }
}

let refreshPromise: Promise<boolean> | null = null

function stored(key: string): string | null {
  return typeof window === 'undefined' ? null : window.localStorage.getItem(key)
}

function clearStoredSession(): void {
  if (typeof window === 'undefined') return
  for (const key of ['signalroom-access-token', 'signalroom-refresh-token', 'signalroom-user']) {
    window.localStorage.removeItem(key)
  }
}

async function refreshSession(): Promise<boolean> {
  const refreshToken = stored('signalroom-refresh-token')
  if (!refreshToken) return false
  if (!refreshPromise) {
    refreshPromise = fetch(
      `${API_BASE_URL}/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
      { method: 'POST', credentials: 'include', headers: { Accept: 'application/json' }, cache: 'no-store' },
    )
      .then(async (response) => {
        if (!response.ok) return false
        const payload = (await response.json()) as { access_token: string; refresh_token: string }
        window.localStorage.setItem('signalroom-access-token', payload.access_token)
        window.localStorage.setItem('signalroom-refresh-token', payload.refresh_token)
        return true
      })
      .catch(() => false)
      .finally(() => { refreshPromise = null })
  }
  const refreshed = await refreshPromise
  if (!refreshed) clearStoredSession()
  return refreshed
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const requestUrl = path.startsWith('http') ? path : `${API_BASE_URL}${path}`
  const request = (token: string | null) =>
    fetch(requestUrl, {
      ...init,
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
      cache: 'no-store',
    })

  let response = await request(stored('signalroom-access-token'))
  if (
    response.status === 401 &&
    !path.includes('/auth/refresh') &&
    !path.includes('/auth/logout') &&
    await refreshSession()
  ) {
    response = await request(stored('signalroom-access-token'))
  }

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as ApiErrorShape | null
    throw new SignalRoomApiError(
      response.status,
      errorBody?.message ?? 'Request failed',
      errorBody?.details,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
