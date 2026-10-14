# SignalRoom API Reference

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/api/v1/docs` (development mode only)

All protected endpoints require:
- `Authorization: Bearer <access_token>` header, OR
- `access_token` cookie (set by login/register)

Multi-org requests may include `X-Organization-ID: <org_id>` header; omitting it uses the user's first org.

---

## Authentication

### `POST /auth/register`
Register a user and create an organisation.
```json
{ "email": "user@example.com", "password": "Password123!", "full_name": "Alex Morgan", "organization_name": "Acme Corp" }
```
Returns: `TokenResponse` with `access_token`, `refresh_token`, `user`, `organization`.

### `POST /auth/login`
Rate-limited: 5 attempts per 15 minutes per IP.
```json
{ "email": "user@example.com", "password": "Password123!" }
```
Returns: `TokenResponse`.

### `POST /auth/refresh`
Rotate refresh token.
```json
{ "refresh_token": "<token>" }
```
Returns: new `TokenResponse`. Old refresh token is revoked.

### `POST /auth/logout`
Revokes the refresh token.

### `GET /auth/me`
Returns authenticated user + organisation + role.

### `POST /auth/password/change`
```json
{ "current_password": "...", "new_password": "NewPass123!" }
```

### `POST /auth/password/forgot`
```json
{ "email": "user@example.com" }
```
Always returns 200 (prevents user enumeration).

### `POST /auth/password/reset`
```json
{ "token": "<reset-token-from-email>", "new_password": "NewPass123!" }
```

---

## Meetings

### `GET /meetings?page=1&limit=20&status=&project_id=&search=`
Paginated meeting list.

### `POST /meetings`
```json
{ "title": "Q4 Planning", "scheduled_start": "2026-10-15T10:00:00Z", "scheduled_end": "2026-10-15T11:00:00Z", "mode": "remote", "project_id": null }
```

### `GET /meetings/{id}`
Full meeting detail including transcript_segments, summary, decisions, action_items, participants, media_file.

### `PATCH /meetings/{id}`
Partial update. Status transitions are validated by state machine.

### `DELETE /meetings/{id}`
Requires owner or admin role.

### `POST /meetings/{id}/archive`
Transitions meeting to `archived`.

### `POST /meetings/{id}/restore`
Transitions archived meeting back to `completed`.

### `POST /meetings/{id}/upload`
**Content-Type: multipart/form-data**
Upload a media file. Accepted formats: `.wav`, `.mp3`, `.m4a`, `.mp4`, `.webm`, `.ogg`, `.mov`, `.flac`
Returns: `{ "meeting_id": "...", "job_id": "...", "filename": "...", "size_bytes": 0, "status": "pending" }`

### `GET /meetings/{id}/job`
Returns current `ProcessingJob` for the meeting:
```json
{ "id": "...", "stage": "transcribe", "status": "processing", "attempts": 1, "error_message": null }
```

### `GET /meetings/{id}/calendar.ics`
Downloads an RFC 5545 ICS calendar event.

### `GET /meetings/{id}/context`
Returns cross-meeting context:
```json
{ "related_meetings": [...], "open_action_items": [...], "recent_decisions": [...] }
```

### `POST /meetings/{id}/agenda`
Generates a structured agenda:
```json
{
  "items": [
    { "order": 1, "title": "Meeting opening", "rationale": "...", "source_type": "overview", "duration_minutes": 5 }
  ],
  "notes": "Estimated total: 45 min."
}
```

---

## Projects

### `GET /projects?page=1&limit=20&status=`
### `POST /projects`
```json
{ "name": "Rebrand", "client": "Acme", "status": "active", "description": "..." }
```
### `GET /projects/{id}`
### `PATCH /projects/{id}`
### `DELETE /projects/{id}` — owner/admin only

---

## Action Items

### `GET /action-items?status=&priority=&meeting_id=&owner_id=&overdue_only=false`
### `POST /action-items`
### `GET /action-items/{id}`
### `PATCH /action-items/{id}`
### `POST /action-items/{id}/complete`
### `POST /action-items/{id}/reassign` `{ "owner_id": "...", "owner_name": "..." }`
### `DELETE /action-items/{id}` — owner/admin only

---

## Decisions

### `GET /decisions?meeting_id=&category=`
### `POST /decisions`
### `DELETE /decisions/{id}` — owner/admin only

---

## Search

### `GET /search?q=pipeline&limit=10`
Hybrid semantic (ChromaDB) + SQL full-text search. Returns:
```json
{
  "query": "pipeline",
  "hits": [
    { "meeting_id": "...", "meeting_title": "...", "content_type": "transcript", "text": "...", "score": 0.85, "metadata": {} }
  ],
  "total": 4
}
```

---

## Dashboard

### `GET /dashboard/aggregates`
Returns counts, upcoming/recent meetings, open action items, recent activity feed.

---

## Notifications

### `GET /notifications?unread_only=false`
### `POST /notifications/{id}/read`
### `POST /notifications/read-all`

---

## Health

### `GET /health/live`
Always 200 if the process is running.

### `GET /health/ready`
Checks database connection and ChromaDB. Returns `status: "ok"` or `"degraded"`.

---

## Error Format

All errors return:
```json
{
  "code": "NOT_FOUND",
  "message": "Meeting not found",
  "details": null,
  "request_id": "uuid"
}
```

Common codes: `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `BAD_REQUEST`, `CONFLICT`, `VALIDATION_ERROR`, `RATE_LIMITED`, `INTERNAL_SERVER_ERROR`.
