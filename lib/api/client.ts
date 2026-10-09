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

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const requestUrl = path.startsWith('http') ? path : `${API_BASE_URL}${path}`
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('signalroom-access-token') : null

  const response = await fetch(requestUrl, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
    cache: 'no-store',
  })

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
