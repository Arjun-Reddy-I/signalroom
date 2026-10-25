'use client'

import { useEffect, useState } from 'react'
import { UsersRound } from 'lucide-react'
import { apiFetch } from '@/lib/api/client'

type Member = {
  id: string
  user_id: string
  role: string
  user: {
    id: string
    email: string
    full_name: string
    avatar_url: string | null
  }
}

type OrgInfo = {
  id: string
  name: string
  slug: string
}

function initials(name: string): string {
  return name
    .split(' ')
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

const ROLE_COLOURS: Record<string, string> = {
  owner: 'avatar-coral',
  admin: 'avatar-amber',
  member: 'avatar-blue',
  viewer: 'avatar-green',
}

export function TeamView() {
  const [me, setMe] = useState<{ user: { full_name: string; email: string }; role: string; organization: OrgInfo } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void apiFetch<{ user: { full_name: string; email: string }; role: string; organization: OrgInfo }>('/auth/me')
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="view-stack">
      <div className="view-heading">
        <div>
          <span className="eyebrow">Workspace members</span>
          <h1>Team</h1>
        </div>
        <UsersRound />
      </div>

      {loading ? (
        <p className="muted-text">Loading team…</p>
      ) : !me ? (
        <p className="muted-text">Team data unavailable.</p>
      ) : (
        <div className="content-grid">
          <section className="panel">
            <div className="section-head">
              <div>
                <span className="eyebrow">Organisation</span>
                <h2>{me.organization.name}</h2>
              </div>
            </div>
            <p className="muted-text">
              Slug: <code>{me.organization.slug}</code>
            </p>

            <div style={{ marginTop: '1.5rem' }}>
              <span className="eyebrow">Your account</span>
              <div className="task-row" style={{ marginTop: '0.75rem' }}>
                <span className={`avatar ${ROLE_COLOURS[me.role] ?? 'avatar-blue'}`}>
                  {initials(me.user.full_name)}
                </span>
                <div>
                  <strong>{me.user.full_name}</strong>
                  <small>{me.user.email}</small>
                </div>
                <span className={`status ${me.role === 'owner' ? 'status-track' : 'status-review'}`}>
                  {me.role}
                </span>
              </div>
            </div>

            <p className="muted-text" style={{ marginTop: '1.5rem' }}>
              Full member listing requires a dedicated memberships API endpoint.
              Your account details are shown above. Use the Settings view to manage
              your profile or invite team members.
            </p>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <span className="eyebrow">Roles</span>
                <h2>Access levels</h2>
              </div>
            </div>
            {[
              { role: 'owner', desc: 'Full access. Can delete the organisation.' },
              { role: 'admin', desc: 'Manage members and all resources.' },
              { role: 'member', desc: 'Create and edit meetings and projects.' },
              { role: 'viewer', desc: 'Read-only access to workspace data.' },
            ].map(({ role, desc }) => (
              <div key={role} className="task-row">
                <span className={`avatar ${ROLE_COLOURS[role] ?? 'avatar-blue'}`} style={{ width: '2rem', height: '2rem', fontSize: '0.6875rem' }}>
                  {role.slice(0, 2).toUpperCase()}
                </span>
                <div>
                  <strong className="role-name">{role}</strong>
                  <small>{desc}</small>
                </div>
                {me.role === role && (
                  <span className="status status-track">You</span>
                )}
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  )
}
