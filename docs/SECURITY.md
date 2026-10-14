# SignalRoom Security Model

## Authentication

**Password hashing**: Argon2id via `passlib[argon2]`. Bcrypt is registered as a fallback for any legacy hashes. Minimum password requirements: 8 characters, uppercase, lowercase, digit (enforced by Pydantic validator on all password fields).

**JWT access tokens**: HS256, 30-minute expiry, include `sub` (user ID), `org_id`, `iat`, `exp`, `type`.

**Refresh tokens**: 64-character random hex (`os.urandom(32).hex()`), SHA-256 hashed before storage. Single-use rotation: each `/auth/refresh` call revokes the old token and issues a new one. The `replaced_by` field creates an audit chain. Tokens are stored as HttpOnly, SameSite=Lax cookies (and also returned in the response body for API clients).

**Password reset**: Tokens are 48-character random hex, SHA-256 hashed in the `users` table, expire in 30 minutes, single-use (cleared after reset). The server always returns the same generic "dispatched" message regardless of whether the email exists (prevents user enumeration).

## Authorisation

**RBAC**: Four roles — owner, admin, member, viewer. Enforced via the `RoleChecker` FastAPI dependency, which loads the `Membership` record for the current user + org and rejects if the role is not in the allowed list.

**Multi-tenant isolation**: All queries are scoped by `organization_id`. `get_current_org` verifies that the authenticated user has a `Membership` record in the requested org before returning it. Cross-org data access returns 403 (verified by `tests/test_tenant_isolation.py`).

**ChromaDB scoping**: All vector queries include `where={"org_id": org.id}`. A user cannot retrieve another org's embeddings via the search API.

## Rate Limiting

The `POST /auth/login` endpoint uses an in-memory sliding-window counter keyed by client IP. After 5 failed attempts within 15 minutes, further attempts return HTTP 429. Successful login resets the counter. This is a single-process solution — for multi-process production, replace with a Redis-backed counter.

## Secrets

**SECRET_KEY**: Used to sign JWTs. Must be changed before production deployment. The application raises `ValueError` at startup if `ENVIRONMENT=production` and the key equals the known default. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`.

**ENCRYPTION_KEY**: 44-byte Fernet key used to encrypt OAuth tokens stored in `calendar_connections`. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

Neither key should ever be committed to version control. Use environment variables or a secrets manager in production.

## File Upload Security

- Extension whitelist: `.wav`, `.mp3`, `.m4a`, `.mp4`, `.webm`, `.ogg`, `.mov`, `.flac`
- File size limit: 250 MB (configurable via `MAX_UPLOAD_SIZE_BYTES`)
- SHA-256 checksum computed on upload and stored for integrity verification
- Randomised storage keys: `{org_id}/{8-byte-random-hex}_{sanitised-filename}` — prevents path traversal and filename collisions
- Path traversal guard in `LocalStorageProvider.get_file_path`: resolves and checks the path stays within `UPLOAD_DIR`
- MIME type stored from the upload but not trusted for content validation; extension check is the primary gate

## Transport Security

- Security headers middleware adds: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`
- CORS: configured via `CORS_ORIGINS_STR`; credentials mode enabled for cookie auth
- Cookies: `HttpOnly=True`, `Secure=True` (production only), `SameSite=lax`

## Sensitive Data Handling

- Passwords are never logged or returned in API responses
- JWT secret is never logged
- Calendar OAuth tokens are encrypted at rest (Fernet)
- Meeting transcripts may contain personal information. Access is scoped to organisation members only.
- No PII is sent to external services unless explicitly configured (e.g., `OPENAI_API_KEY` set)
- Demo/fallback mode operates entirely locally

## Known Limitations

1. Rate limiting is in-memory — restarting the process resets attempt counters
2. No CSRF protection (relied upon by `SameSite=lax` cookies for browser-initiated requests)
3. No refresh token reuse detection (detecting reuse of a revoked token does not automatically revoke the entire family)
4. No account lockout based on email (only per-IP) — a distributed attack from many IPs is not mitigated
5. No audit event for password reset (should be added)
6. Local model inference (Whisper, Ollama) processes audio locally — no data leaves the machine
7. OpenAI/external providers send transcripts to third-party servers — document this in your deployment
