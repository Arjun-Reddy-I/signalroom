'use client'

import { useEffect, useState } from 'react'
import { CalendarDays, Clock, Download } from 'lucide-react'
import { apiFetch } from '@/lib/api/client'

type MeetingRow = {
  id: string
  title: string
  scheduled_start: string
  scheduled_end: string
  status: string
  mode: string
}

type ActionItemRow = {
  id: string
  title: string
  owner_name: string | null
  due_date: string | null
  priority: string
  status: string
}

type Aggregates = {
  upcoming_meetings: MeetingRow[]
  action_items: ActionItemRow[]
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function CalendarView() {
  const [data, setData] = useState<Aggregates | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void apiFetch<Aggregates>('/dashboard/aggregates')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  const dueSoon = data?.action_items.filter((a) => {
    if (!a.due_date || a.status === 'completed') return false
    const due = new Date(a.due_date)
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() + 7)
    return due <= cutoff
  })

  return (
    <div className="view-stack">
      <div className="view-heading">
        <div>
          <span className="eyebrow">Schedule</span>
          <h1>Calendar</h1>
        </div>
        <CalendarDays />
      </div>

      {loading ? (
        <p className="muted-text">Loading calendar…</p>
      ) : !data ? (
        <p className="muted-text">Calendar unavailable. Ensure the API is running.</p>
      ) : (
        <div className="content-grid">
          {/* Upcoming meetings */}
          <section className="panel">
            <div className="section-head">
              <div>
                <span className="eyebrow">Next up</span>
                <h2>Upcoming meetings</h2>
              </div>
              <CalendarDays />
            </div>
            {data.upcoming_meetings.length === 0 ? (
              <p className="muted-text">No upcoming meetings scheduled.</p>
            ) : (
              data.upcoming_meetings.map((m) => (
                <div key={m.id} className="task-row">
                  <div>
                    <strong>{m.title}</strong>
                    <small>{formatDateTime(m.scheduled_start)}</small>
                  </div>
                  <span className={`status ${m.status === 'completed' ? 'status-track' : 'status-review'}`}>
                    {m.status}
                  </span>
                  <a
                    href={`/api/meetings/${m.id}/calendar.ics`}
                    className="text-button"
                    download
                    title="Download ICS"
                  >
                    <Download style={{ width: '1rem' }} />
                  </a>
                </div>
              ))
            )}
          </section>

          {/* Due this week */}
          <section className="panel">
            <div className="section-head">
              <div>
                <span className="eyebrow">Action items</span>
                <h2>Due this week</h2>
              </div>
              <Clock />
            </div>
            {!dueSoon || dueSoon.length === 0 ? (
              <p className="muted-text">No action items due in the next 7 days.</p>
            ) : (
              dueSoon.map((a) => (
                <div key={a.id} className={`task-row ${a.status === 'completed' ? 'task-done' : ''}`}>
                  <div>
                    <strong>{a.title}</strong>
                    <small>
                      {a.owner_name ?? 'Unassigned'} · due {a.due_date ? formatDate(a.due_date) : '—'}
                    </small>
                  </div>
                  <span className={`priority ${a.priority}`}>{a.priority}</span>
                  <span className={`status ${a.status === 'completed' ? 'status-track' : new Date(a.due_date ?? '') < new Date() ? 'status-risk' : 'status-review'}`}>
                    {a.status}
                  </span>
                </div>
              ))
            )}
          </section>
        </div>
      )}
    </div>
  )
}
