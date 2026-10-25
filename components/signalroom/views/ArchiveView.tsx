'use client'

import { useEffect, useState } from 'react'
import { Archive, ChevronRight } from 'lucide-react'
import { apiFetch } from '@/lib/api/client'

type Meeting = {
  id: string
  title: string
  scheduled_start: string
  status: string
  mode: string
  project_id: string | null
}

type PaginatedMeetings = {
  items: Meeting[]
  total: number
}

export function ArchiveView() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    void apiFetch<PaginatedMeetings>('/meetings?status=archived&limit=50')
      .then((res) => {
        setMeetings(res.items)
        setTotal(res.total)
      })
      .catch(() => setMeetings([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="view-stack">
      <div className="view-heading">
        <div>
          <span className="eyebrow">Historical records</span>
          <h1>Archive</h1>
        </div>
        <Archive />
      </div>

      <section className="panel">
        <div className="section-head">
          <div>
            <span className="eyebrow">{total} archived</span>
            <h2>Archived meetings</h2>
          </div>
        </div>

        {loading ? (
          <p className="muted-text">Loading archive…</p>
        ) : meetings.length === 0 ? (
          <div className="empty-state">
            <Archive />
            <strong>No archived meetings</strong>
            <span>Meetings you archive will appear here.</span>
          </div>
        ) : (
          meetings.map((m) => (
            <a
              key={m.id}
              href={`/meetings/${m.id}`}
              className="task-row"
            >
              <div>
                <strong>{m.title}</strong>
                <small>
                  {new Date(m.scheduled_start).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}{' '}
                  · {m.mode}
                </small>
              </div>
              <span className="status status-review">archived</span>
              <ChevronRight style={{ width: '1rem', color: 'var(--muted-foreground)' }} />
            </a>
          ))
        )}
      </section>
    </div>
  )
}
