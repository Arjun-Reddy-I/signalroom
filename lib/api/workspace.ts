import { apiFetch } from '@/lib/api/client'

export type CreateProjectRequest = {
  name: string
  client: string
}

export type UpdateActionItemRequest = {
  status?: 'open' | 'in_progress' | 'completed'
}

export async function createProjectRequest(input: CreateProjectRequest) {
  return apiFetch('/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export async function updateActionItemRequest(id: string, input: UpdateActionItemRequest) {
  return apiFetch(`/action-items/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export async function markNotificationReadRequest(id: string) {
  return apiFetch(`/notifications/${id}/read`, { method: 'POST' })
}
